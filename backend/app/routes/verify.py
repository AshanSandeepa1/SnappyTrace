import os
import shutil
import json
import hashlib
from app.pades import verify_pdf_signature_async
from app.ai.pdf_utils import compute_canonical_hash, rasterize_pages_and_hashes
from app.ai.ocr import extract_text_from_pdf
from app.ai.semantic import combined_similarity, short_diff_summary
from uuid import uuid4

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from app.ai.embed import extract_watermark_ai
from app.ai.fingerprint import dhash_path, hamming_distance_hex64
from app.database import db

router = APIRouter()

UPLOAD_DIR = "/tmp/snappy_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _normalize_metadata(value):
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None
    return None


def _extract_common_fields_from_record(record):
    """Shape DB record into common verification response fields."""
    md = _normalize_metadata(record.get("metadata"))
    return {
        "watermark_id": record.get("watermark_id"),
        "watermark_code": record.get("watermark_code"),
        "issued_at": record.get("issued_at").isoformat() if record.get("issued_at") else None,
        "source_created_at": record.get("source_created_at").isoformat() if record.get("source_created_at") else None,
        "metadata": md,
        # Convenience copies (UI-friendly) for common metadata keys.
        "title": md.get("title") if isinstance(md, dict) else None,
        "author": md.get("author") if isinstance(md, dict) else None,
        "organization": md.get("organization") if isinstance(md, dict) else None,
        "createdDate": md.get("createdDate") if isinstance(md, dict) else None,
    }


@router.post("/verify")
async def verify_file(file: UploadFile = File(...), debug: bool = False):
    """Verify a watermark by extracting it from an uploaded file."""
    filename = f"verify_{uuid4().hex}_{file.filename}"
    temp_path = os.path.join(UPLOAD_DIR, filename)
    extracted = None

    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Branch by file type: PDF verification flow or image watermark flow
        is_pdf = file.filename.lower().endswith(".pdf") or file.content_type == "application/pdf"

        if is_pdf:
            debug_info = {
                "is_pdf": True,
                "filename": file.filename,
            } if debug else None

            # 1) Try authoritative PAdES signature verification
            pades_res = await verify_pdf_signature_async(temp_path)
            if debug_info is not None:
                debug_info["pades_valid"] = bool(pades_res.get("valid"))
                debug_info["pades_thumbprint"] = pades_res.get("signer_cert_thumbprint")
            if pades_res.get("valid") and pades_res.get("signer_cert_thumbprint"):
                thumb = pades_res.get("signer_cert_thumbprint")

                # Prefer exact file hash lookup first. This is stable even when many
                # files are signed with the same demo certificate.
                sha256 = None
                try:
                    with open(temp_path, "rb") as f:
                        sha256 = hashlib.sha256(f.read()).hexdigest()
                except Exception:
                    sha256 = None
                if debug_info is not None:
                    debug_info["sha256"] = sha256

                record = None
                if sha256:
                    record = await db.fetch_one(
                        """
                        SELECT wf.*, u.name as owner_name, u.email as owner_email
                        FROM watermarked_files wf
                        JOIN users u ON u.id = wf.user_id
                        WHERE wf.original_file_hash=$1
                        """,
                        sha256,
                    )

                # Fallback: thumbprint lookup only if it uniquely identifies a single record
                if not record and thumb:
                    rows = await db.fetch_all(
                        """
                        SELECT wf.*, u.name as owner_name, u.email as owner_email
                        FROM watermarked_files wf
                        JOIN users u ON u.id = wf.user_id
                        WHERE wf.signer_cert_thumbprint=$1
                        """,
                        thumb,
                    )
                    if rows and len(rows) == 1:
                        record = rows[0]
                    elif rows and len(rows) > 1:
                        # Signature is valid, but we cannot map ownership uniquely.
                        if debug_info is not None:
                            debug_info["thumbprint_rows"] = len(rows)
                            print("[verify debug] ambiguous thumbprint match", debug_info)
                        return JSONResponse(
                            {
                                "valid": False,
                                "signature_valid": True,
                                "tamper_suspected": False,
                                "method": "pades",
                                "signer_cert_thumbprint": thumb,
                                "reason": "signature valid but cannot uniquely map owner (shared signing cert)",
                                "note": "Re-verify using the exact file downloaded from this system, or use per-user certificates in production.",
                                **({"debug": debug_info} if debug_info is not None else {}),
                            }
                        )

                if record:
                    # Run OCR + semantic comparator against stored metadata (if present)
                    ai_text = None
                    ai_score = None
                    ai_flag = None
                    ai_diff = None
                    try:
                        texts = extract_text_from_pdf(temp_path, dpi=150, max_pages=5)
                        ai_text = "\n---\n".join([t.strip() for t in texts if t.strip()])[:1000]
                        # Compare concatenated OCR text to metadata/title/author for a rough semantic check
                        ref = ""
                        md = _normalize_metadata(record.get("metadata"))
                        if isinstance(md, dict):
                            ref = " ".join(filter(None, [md.get("title"), md.get("author"), md.get("organization"), md.get("createdDate")]))
                        ai_score = combined_similarity(ai_text, ref) if ref else None
                        ai_flag = False if (ai_score is None or ai_score >= 0.8) else True
                        ai_diff = short_diff_summary(ai_text, ref) if ref else None
                    except Exception:
                        ai_text = None

                    resp = {
                        "valid": True,
                        "confidence": 1.0,
                        "tamper_suspected": False,
                        "method": "pades",
                        **_extract_common_fields_from_record(record),
                        "owner": {"name": record["owner_name"], "email": record["owner_email"]},
                        "signed_at": record.get("signed_at").isoformat() if record.get("signed_at") else None,
                        "signer_cert_thumbprint": record.get("signer_cert_thumbprint"),
                        "note": "Authoritative PAdES signature validated and mapped to owner.",
                    }
                    if ai_text is not None:
                        resp.update({
                            "ai_ocr_text": ai_text,
                            "ai_text_similarity_score": ai_score,
                            "ai_tamper_flag": ai_flag,
                            "ai_text_diff_summary": ai_diff,
                        })
                    if debug_info is not None:
                        debug_info["method"] = "pades"
                        print("[verify debug] pades mapped", debug_info)
                        resp["debug"] = debug_info
                    return JSONResponse(resp)

            # 2) Canonical content hashing (born-digital)
            # Disabled: `metadata_hash` is the hash of user-entered metadata, not PDF canonical content.
            # Enabling canonical matching requires a dedicated DB column for canonical PDF content hashes.

            # 3) Scanned / image-like PDFs: compute per-page dhash and try perceptual match
            try:
                page_hashes = rasterize_pages_and_hashes(temp_path, dpi=150, max_pages=5)
            except Exception:
                page_hashes = []

            if debug_info is not None:
                debug_info["query_page_hashes"] = len(page_hashes)

            if page_hashes:
                # search DB for candidate rows with per_page_hashes present
                candidates = await db.fetch_all(
                    """
                    SELECT wf.*, u.name as owner_name, u.email as owner_email
                    FROM watermarked_files wf
                    JOIN users u ON u.id = wf.user_id
                    WHERE wf.per_page_hashes IS NOT NULL
                    ORDER BY wf.issued_at DESC
                    LIMIT 500
                    """
                )

                best = None
                best_score = -1
                second_best_score = -1
                import math

                # Tuning knobs for perceptual PDF matching.
                # Print-to-PDF and re-save operations can introduce small rasterization differences.
                # We relax the per-page threshold a bit, but we also require a gap between the
                # best and second-best candidates to reduce false positives.
                PAGE_DHASH_THRESHOLD = 16
                MIN_SCORE = 0.4
                MIN_GAP_SCORE = 0.10
                if debug_info is not None:
                    debug_info.update({
                        "PAGE_DHASH_THRESHOLD": PAGE_DHASH_THRESHOLD,
                        "MIN_SCORE": MIN_SCORE,
                        "MIN_GAP_SCORE": MIN_GAP_SCORE,
                        "candidate_limit": 500,
                    })

                # Coerce candidate rows' per_page_hashes into Python lists robustly.
                parsed_candidates = []
                for row in candidates:
                    try:
                        per = row.get("per_page_hashes")
                        if per is None:
                            continue
                        if isinstance(per, str):
                            try:
                                per = json.loads(per)
                            except Exception:
                                per = []
                        if not isinstance(per, list) or len(per) == 0:
                            continue
                        parsed_candidates.append((row, per))
                    except Exception:
                        continue

                for row, per in parsed_candidates:
                    # Robust overlap score:
                    # For each query page, consider it a match if it is close to *any* candidate page.
                    # This is more resilient to PDF rewrites (Print-to-PDF/resave) that can shift ordering.
                    candidate_hashes = []
                    for candidate in per:
                        try:
                            if isinstance(candidate, dict):
                                candidate_hex = candidate.get("dhash")
                            else:
                                candidate_hex = candidate
                            if candidate_hex:
                                candidate_hashes.append(candidate_hex)
                        except Exception:
                            continue

                    if not candidate_hashes:
                        continue

                    matches = 0
                    total = len(page_hashes)
                    for qh in page_hashes:
                        try:
                            best_d = None
                            for ch in candidate_hashes:
                                d = hamming_distance_hex64(qh, ch)
                                if best_d is None or d < best_d:
                                    best_d = d
                            if best_d is not None and best_d <= PAGE_DHASH_THRESHOLD:
                                matches += 1
                        except Exception:
                            continue

                    score = matches / max(1, total)
                    if score > best_score:
                        second_best_score = best_score
                        best_score = score
                        best = row
                    elif score > second_best_score:
                        second_best_score = score

                # best_score and best candidate selected

                if debug_info is not None:
                    debug_info["best_score"] = float(best_score)
                    debug_info["second_best_score"] = float(second_best_score)
                    debug_info["best_gap"] = float(best_score - second_best_score)
                    debug_info["best_watermark_code"] = best.get("watermark_code") if best is not None else None

                if best is not None and best_score >= MIN_SCORE and (best_score - second_best_score) >= MIN_GAP_SCORE:
                    # Build base response for perceptual match
                    resp = {
                        "valid": False,
                        "ownership_confidence": float(best_score),
                        "tamper_suspected": best_score < 0.7,
                        "method": "perceptual_pdf",
                        **_extract_common_fields_from_record(best),
                        "owner": {"name": best["owner_name"], "email": best["owner_email"]},
                        "note": "Per-page perceptual match; not authoritative.",
                    }

                    # Attempt OCR + semantic comparison against stored metadata for better diagnostics
                    try:
                        texts = extract_text_from_pdf(temp_path, dpi=150, max_pages=5)
                        ai_text = "\n---\n".join([t.strip() for t in texts if t.strip()])[:1000]
                        md = _normalize_metadata(best.get("metadata"))
                        ref = ""
                        if isinstance(md, dict):
                            ref = " ".join(filter(None, [md.get("title"), md.get("author"), md.get("organization"), md.get("createdDate")]))
                        ai_score = combined_similarity(ai_text, ref) if ref else None
                        ai_flag = False if (ai_score is None or ai_score >= 0.8) else True
                        ai_diff = short_diff_summary(ai_text, ref) if ref else None
                        if ai_flag is True:
                            resp["tamper_suspected"] = True
                        resp.update({
                            "ai_ocr_text": ai_text,
                            "ai_text_similarity_score": ai_score,
                            "ai_tamper_flag": ai_flag,
                            "ai_text_diff_summary": ai_diff,
                        })
                    except Exception:
                        # If OCR fails, just return the perceptual match response
                        pass

                    if debug_info is not None:
                        debug_info["method"] = "perceptual_pdf"
                        print("[verify debug] perceptual match", debug_info)
                        resp["debug"] = debug_info

                    return JSONResponse(resp)

            if debug_info is not None:
                debug_info["method"] = "no_match"
                print("[verify debug] no match", debug_info)
                return JSONResponse({"valid": False, "reason": "no authoritative signature and no perceptual match", "debug": debug_info})

            return JSONResponse({"valid": False, "reason": "no authoritative signature and no perceptual match"})

        # Non-PDF path: existing image watermark flow
        extracted = extract_watermark_ai(temp_path)

        if extracted.get("valid"):
            watermark_id = extracted.get("watermark_id")
            watermark_code = extracted.get("watermark_code")
            confidence = float(extracted.get("confidence") or 0.0)

            record = await db.fetch_one(
                """
                SELECT wf.watermark_id, wf.watermark_code, wf.original_filename, wf.mime_type,
                       wf.original_file_hash, wf.metadata, wf.metadata_hash, wf.source_created_at, wf.issued_at,
                       u.name as owner_name, u.email as owner_email
                FROM watermarked_files wf
                JOIN users u ON u.id = wf.user_id
                WHERE wf.watermark_id=$1
                """,
                watermark_id,
            )

            if not record:
                return JSONResponse(
                    {
                        "valid": False,
                        "confidence": confidence,
                        "tamper_suspected": True,
                        "reason": "watermark extracted but not found in DB",
                        "watermark_id": watermark_id,
                        "watermark_code": watermark_code,
                    }
                )

            tamper_suspected = confidence < 0.55
            return JSONResponse(
                {
                    "valid": True,
                    "confidence": confidence,
                    "tamper_suspected": tamper_suspected,
                    "watermark_id": record["watermark_id"],
                    "watermark_code": record["watermark_code"],
                    "owner": {"name": record["owner_name"], "email": record["owner_email"]},
                    "issued_at": record["issued_at"].isoformat() if record["issued_at"] else None,
                    "source_created_at": record["source_created_at"].isoformat() if record["source_created_at"] else None,
                    "metadata": _normalize_metadata(record.get("metadata")),
                    "metadata_hash": record["metadata_hash"],
                    "original_filename": record["original_filename"],
                    "mime_type": record["mime_type"],
                }
            )

        # Watermark not readable: try perceptual-hash fallback (must run before cleanup).
        confidence = float(extracted.get("confidence") or 0.0)
        query_hash = None
        try:
            query_hash = dhash_path(temp_path)
        except Exception:
            query_hash = None

        if not query_hash:
            raise HTTPException(status_code=400, detail=extracted.get("reason") or "Watermark not found")

        fallback = None
        try:
            candidates = await db.fetch_all(
                """
                SELECT wf.watermark_id, wf.watermark_code, wf.original_filename, wf.mime_type,
                       wf.original_file_hash, wf.metadata, wf.metadata_hash, wf.source_created_at, wf.issued_at,
                       wf.perceptual_hash,
                       u.name as owner_name, u.email as owner_email
                FROM watermarked_files wf
                JOIN users u ON u.id = wf.user_id
                WHERE wf.perceptual_hash IS NOT NULL
                ORDER BY wf.issued_at DESC
                LIMIT 500
                """
            )

            best = None
            best_dist = None
            second_best_dist = None
            for row in candidates:
                ph = row.get("perceptual_hash")
                if not ph:
                    continue
                dist = hamming_distance_hex64(query_hash, ph)
                if best is None or dist < best_dist:
                    second_best_dist = best_dist
                    best = row
                    best_dist = dist
                elif second_best_dist is None or dist < second_best_dist:
                    second_best_dist = dist

            # Stricter fallback to reduce false matches (e.g. original vs watermarked).
            # - Lower threshold
            # - Require a gap vs the second-best match
            # Threshold tuning:
            # - Higher threshold helps crops match again.
            # - Keep the second-best gap so we don't match too many unrelated images.
            DHASH_THRESHOLD = 10
            MIN_GAP = 2

            if (
                best is not None
                and best_dist is not None
                and best_dist <= DHASH_THRESHOLD
                and (second_best_dist is None or (best_dist + MIN_GAP) <= second_best_dist)
            ):
                fallback = {
                    "match": True,
                    "method": "perceptual_hash",
                    "hamming_distance": int(best_dist),
                    "match_type": "possible",
                    "note": "Similarity match only; watermark could not be decoded from this file.",
                    "owner": {"name": best["owner_name"], "email": best["owner_email"]},
                    "issued_at": best["issued_at"].isoformat() if best["issued_at"] else None,
                    "source_created_at": best["source_created_at"].isoformat() if best["source_created_at"] else None,
                    "metadata": _normalize_metadata(best.get("metadata")),
                    "metadata_hash": best["metadata_hash"],
                    "original_filename": best["original_filename"],
                    "mime_type": best["mime_type"],
                }
        except Exception:
            fallback = None

        return JSONResponse(
            {
                "valid": False,
                "confidence": confidence,
                "tamper_suspected": confidence < 0.35,
                "reason": extracted.get("reason") or "watermark not found",
                "fallback": fallback,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            os.remove(temp_path)
        except Exception:
            pass


@router.get("/verify/{watermark}")
async def verify_by_id(watermark: str):
    """Verify by watermark id/code only (no file tamper check).

    This is useful for quick lookups from the UI. Authenticity of a *file* still
    requires uploading the file for extraction.
    """
    try:
        token = os.path.basename(watermark.strip())
        # Allow pasting of filenames like WMK-XXXX.png or URLs.
        token = os.path.splitext(token)[0]
        token_upper = token.upper()

        if token_upper.startswith("WMK-"):
            record = await db.fetch_one(
                """
                SELECT wf.watermark_id, wf.watermark_code, wf.original_filename, wf.mime_type,
                       wf.metadata, wf.metadata_hash, wf.source_created_at, wf.issued_at,
                       u.name as owner_name, u.email as owner_email
                FROM watermarked_files wf
                JOIN users u ON u.id = wf.user_id
                WHERE wf.watermark_code=$1
                """,
                token_upper,
            )
        else:
            record = await db.fetch_one(
                """
                SELECT wf.watermark_id, wf.watermark_code, wf.original_filename, wf.mime_type,
                       wf.metadata, wf.metadata_hash, wf.source_created_at, wf.issued_at,
                       u.name as owner_name, u.email as owner_email
                FROM watermarked_files wf
                JOIN users u ON u.id = wf.user_id
                WHERE wf.watermark_id=$1
                """,
                token.lower(),
            )

        if not record:
            return {
                "valid": False,
                "reason": "not found",
                "file_required": False,
            }

        return {
            "valid": True,
            "file_required": True,
            "watermark_id": record["watermark_id"],
            "watermark_code": record["watermark_code"],
            "owner": {"name": record["owner_name"], "email": record["owner_email"]},
            "issued_at": record["issued_at"].isoformat() if record["issued_at"] else None,
            "source_created_at": record["source_created_at"].isoformat() if record["source_created_at"] else None,
            "metadata": _normalize_metadata(record.get("metadata")),
            "metadata_hash": record["metadata_hash"],
            "original_filename": record["original_filename"],
            "mime_type": record["mime_type"],
            "note": "Upload the file to check tampering and match confidence.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
