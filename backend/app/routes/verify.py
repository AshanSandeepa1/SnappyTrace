import os
import shutil
import json
import hashlib
from app.pades import verify_pdf_signature_async
from app.ai.pdf_utils import compute_canonical_hash, rasterize_pages_and_hashes
from app.ai.ocr import extract_text_from_pdf
from app.ai.semantic import combined_similarity, short_diff_summary
from app.ai.text_fingerprint import simhash64_hex
from uuid import uuid4

try:
    import fitz
except Exception:
    fitz = None

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


def _pdf_text_simhash_from_path(path: str) -> str | None:
    """Best-effort text fingerprint for a PDF file.

    Prefer embedded text via PyMuPDF; fallback to OCR for scanned PDFs.
    Returns 16-hex string (64-bit simhash) or None if insufficient text.
    """
    text = ""

    if fitz is not None:
        try:
            doc = fitz.open(path)
            try:
                parts = []
                for i in range(min(3, doc.page_count)):
                    try:
                        parts.append(doc.load_page(i).get_text("text") or "")
                    except Exception:
                        continue
                text = "\n".join(parts)
            finally:
                doc.close()
        except Exception:
            text = ""

    if not (text or "").strip():
        try:
            ocr_pages = extract_text_from_pdf(path, dpi=150, max_pages=3)
            text = "\n".join([t for t in ocr_pages if t])
        except Exception:
            text = ""

    return simhash64_hex(text)


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
                # Hash more pages to reduce collisions (short PDFs often tie at 1.0).
                page_hashes = rasterize_pages_and_hashes(temp_path, dpi=150, max_pages=10)
            except Exception:
                page_hashes = []

            if debug_info is not None:
                debug_info["query_page_hashes"] = len(page_hashes)

            if page_hashes:
                query_text_simhash = None
                try:
                    query_text_simhash = _pdf_text_simhash_from_path(temp_path)
                except Exception:
                    query_text_simhash = None

                if debug_info is not None:
                    debug_info["query_text_simhash_present"] = bool(query_text_simhash)

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
                best_score = -1.0
                best_dist_score = -1.0
                best_avg_distance = None
                best_text_score = -1.0
                best_text_dist = None

                second_best_score = -1.0
                second_best_dist_score = -1.0
                second_best_avg_distance = None
                second_best_text_score = -1.0
                second_best_text_dist = None
                import math

                # Tuning knobs for perceptual PDF matching.
                # Print-to-PDF and re-save operations can introduce small rasterization differences.
                # We relax the per-page threshold a bit, but we also require a gap between the
                # best and second-best candidates to reduce false positives.
                PAGE_DHASH_THRESHOLD = 16
                # IMPORTANT: This score is a page-overlap ratio. When the query PDF is only 1 page,
                # it's easy to find accidental overlaps among many candidates. We therefore keep
                # a conservative minimum.
                MIN_SCORE = 0.8
                MIN_GAP_SCORE = 0.10
                # Secondary gap when scores tie (e.g., best_score==second_best_score==1.0).
                # Uses a derived distance score (1 - avg_min_hamming/64).
                MIN_GAP_DIST_SCORE = 0.03
                # Require an absolute distance-quality threshold as well; otherwise a random PDF
                # can still get score=1.0 for short documents.
                MIN_DIST_SCORE = 0.82
                # Dual-factor integrity check: when we can extract enough text,
                # require a close SimHash match as well.
                TEXT_SIMHASH_MAX_DIST = 12
                if debug_info is not None:
                    debug_info.update({
                        "PAGE_DHASH_THRESHOLD": PAGE_DHASH_THRESHOLD,
                        "MIN_SCORE": MIN_SCORE,
                        "MIN_GAP_SCORE": MIN_GAP_SCORE,
                        "MIN_GAP_DIST_SCORE": MIN_GAP_DIST_SCORE,
                        "MIN_DIST_SCORE": MIN_DIST_SCORE,
                        "TEXT_SIMHASH_MAX_DIST": TEXT_SIMHASH_MAX_DIST,
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

                scored_candidates = []

                # Rank tuple: (visual overlap score, distance quality score, text agreement rank, text score)
                # Higher is better for all components.
                best_rank = (-1.0, -1.0, -1, -1.0)
                second_rank = (-1.0, -1.0, -1, -1.0)

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
                    min_distances = []
                    for qh in page_hashes:
                        try:
                            best_d = None
                            for ch in candidate_hashes:
                                d = hamming_distance_hex64(qh, ch)
                                if best_d is None or d < best_d:
                                    best_d = d
                            if best_d is None:
                                continue
                            min_distances.append(int(best_d))
                            if best_d <= PAGE_DHASH_THRESHOLD:
                                matches += 1
                        except Exception:
                            continue

                    score = matches / max(1, total)
                    # Secondary signal: prefer the candidate with smaller average min distance.
                    # Convert to a 0..1 score where 1 is best.
                    if min_distances:
                        avg_distance = float(sum(min_distances)) / float(len(min_distances))
                    else:
                        avg_distance = 64.0
                    dist_score = 1.0 - (min(64.0, max(0.0, avg_distance)) / 64.0)

                    # Optional text fingerprint gate.
                    text_score = None
                    text_dist = None
                    text_ok = None
                    if query_text_simhash:
                        cand_simhash = row.get("pdf_text_simhash")
                        if cand_simhash:
                            try:
                                text_dist = hamming_distance_hex64(query_text_simhash, cand_simhash)
                                text_score = 1.0 - (min(64.0, max(0.0, float(text_dist))) / 64.0)
                                text_ok = int(text_dist) <= int(TEXT_SIMHASH_MAX_DIST)
                            except Exception:
                                text_ok = False
                        else:
                            # Older records may not have the fingerprint populated yet.
                            # Treat as unknown, not a hard mismatch.
                            text_ok = None

                    # Keep a small scored list for ambiguity handling/debug.
                    scored_candidates.append(
                        {
                            "row": row,
                            "score": float(score),
                            "dist_score": float(dist_score),
                            "avg_distance": float(avg_distance),
                            "text_score": float(text_score) if text_score is not None else None,
                            "text_dist": int(text_dist) if text_dist is not None else None,
                            "text_ok": bool(text_ok) if text_ok is not None else None,
                        }
                    )

                    # Rank candidates. When query text fingerprint is available, prefer
                    # candidates that also match the text fingerprint.
                    if query_text_simhash:
                        if text_ok is True:
                            text_rank = 2
                        elif text_ok is None:
                            text_rank = 1
                        else:
                            text_rank = 0
                    else:
                        text_rank = 1

                    ts = float(text_score) if text_score is not None else -1.0
                    candidate_rank = (float(score), float(dist_score), int(text_rank), float(ts))

                    if candidate_rank > best_rank:
                        # Demote current best to second best
                        second_rank = best_rank
                        second_best_score = best_score
                        second_best_dist_score = best_dist_score
                        second_best_avg_distance = best_avg_distance
                        second_best_text_score = best_text_score
                        second_best_text_dist = best_text_dist

                        # Promote candidate to best
                        best_rank = candidate_rank
                        best_score = float(score)
                        best_dist_score = float(dist_score)
                        best_avg_distance = float(avg_distance)
                        best_text_score = float(ts)
                        best_text_dist = int(text_dist) if text_dist is not None else None
                        best = row
                    elif candidate_rank > second_rank:
                        second_rank = candidate_rank
                        second_best_score = float(score)
                        second_best_dist_score = float(dist_score)
                        second_best_avg_distance = float(avg_distance)
                        second_best_text_score = float(ts)
                        second_best_text_dist = int(text_dist) if text_dist is not None else None

                # best_score and best candidate selected

                if debug_info is not None:
                    debug_info["best_score"] = float(best_score)
                    debug_info["second_best_score"] = float(second_best_score)
                    debug_info["best_gap"] = float(best_score - second_best_score)
                    debug_info["best_watermark_code"] = best.get("watermark_code") if best is not None else None
                    debug_info["best_avg_distance"] = float(best_avg_distance) if best_avg_distance is not None else None
                    debug_info["second_best_avg_distance"] = float(second_best_avg_distance) if second_best_avg_distance is not None else None
                    debug_info["best_dist_score"] = float(best_dist_score)
                    debug_info["second_best_dist_score"] = float(second_best_dist_score)
                    debug_info["best_dist_gap"] = float(best_dist_score - second_best_dist_score)
                    debug_info["best_text_score"] = float(best_text_score) if best_text_score is not None else None
                    debug_info["second_best_text_score"] = float(second_best_text_score) if second_best_text_score is not None else None
                    debug_info["best_text_dist"] = int(best_text_dist) if best_text_dist is not None else None
                    debug_info["second_best_text_dist"] = int(second_best_text_dist) if second_best_text_dist is not None else None

                score_gap_ok = (best_score - second_best_score) >= MIN_GAP_SCORE
                dist_gap_ok = (best_dist_score - second_best_dist_score) >= MIN_GAP_DIST_SCORE

                # Short PDFs are inherently less reliable. Apply stricter rules based on
                # the amount of available signal.
                query_pages = len(page_hashes)
                if query_pages <= 1:
                    # Never auto-assign a single owner from 1 page.
                    score_gap_ok = False
                    dist_gap_ok = False
                elif query_pages == 2:
                    # Still fairly small; require stronger separation.
                    MIN_GAP_DIST_SCORE = max(MIN_GAP_DIST_SCORE, 0.04)
                    MIN_DIST_SCORE = max(MIN_DIST_SCORE, 0.85)
                    if debug_info is not None:
                        debug_info["MIN_GAP_DIST_SCORE"] = MIN_GAP_DIST_SCORE
                        debug_info["MIN_DIST_SCORE"] = MIN_DIST_SCORE

                # Only accept a unique match if it passes both overlap (best_score) and
                # distance-quality (best_dist_score) checks.
                text_gate_ok = True
                if query_text_simhash:
                    text_gate_ok = best_text_dist is not None and int(best_text_dist) <= int(TEXT_SIMHASH_MAX_DIST)

                # If we couldn't extract enough text from the query, keep the system
                # conservative: do not auto-map ownership from perceptual matching.
                if not query_text_simhash:
                    text_gate_ok = False

                if (
                    best is not None
                    and best_score >= MIN_SCORE
                    and best_dist_score >= MIN_DIST_SCORE
                    and (score_gap_ok or dist_gap_ok)
                    and text_gate_ok
                ):
                    # Build base response for perceptual match
                    resp = {
                        "valid": False,
                        "ownership_confidence": float(best_score),
                        "tamper_suspected": best_dist_score < 0.9,
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

                # If we have a decent match but it's ambiguous (ties), surface that to the user
                # instead of returning a generic no_match.
                if best is not None and best_score >= MIN_SCORE and scored_candidates:
                    try:
                        pool = scored_candidates
                        if query_text_simhash:
                            # Prefer text-consistent candidates first, but keep "unknown" (missing fingerprint)
                            # as a fallback so we can explain what's happening.
                            pool = [c for c in scored_candidates if c.get("text_ok") is not False]

                        pool.sort(key=lambda x: (x.get("score", 0.0), x.get("dist_score", 0.0), x.get("text_score") or 0.0), reverse=True)
                        if not pool:
                            pool = scored_candidates
                        top = pool[0]
                        top_score = float(top.get("score", 0.0))
                        top_dist_score = float(top.get("dist_score", 0.0))

                        # If we couldn't extract enough text from the query PDF, we refuse to
                        # auto-map ownership and instead surface the best candidates explicitly.
                        if not query_text_simhash and query_pages >= 2:
                            resp = {
                                "valid": False,
                                "ownership_confidence": float(top_score),
                                "tamper_suspected": True,
                                "method": "perceptual_pdf_ambiguous",
                                "note": "Perceptual match found, but not enough text could be extracted to confirm ownership. Cannot uniquely identify the owner.",
                                "candidates": [],
                            }
                            r = (top.get("row") or {})
                            resp["candidates"].append(
                                {
                                    "watermark_code": r.get("watermark_code"),
                                    "watermark_id": r.get("watermark_id"),
                                    "issued_at": r.get("issued_at").isoformat() if r.get("issued_at") else None,
                                    "owner": {"name": r.get("owner_name"), "email": r.get("owner_email")},
                                    "score": float(top.get("score", 0.0)),
                                    "dist_score": float(top.get("dist_score", 0.0)),
                                    "text_score": top.get("text_score"),
                                    "text_dist": top.get("text_dist"),
                                }
                            )
                            if debug_info is not None:
                                debug_info["method"] = "perceptual_pdf_ambiguous"
                                resp["debug"] = debug_info
                            return JSONResponse(resp)

                        # If the query has a text fingerprint but the top candidate doesn't,
                        # we also refuse to auto-map and explain why.
                        if query_text_simhash and top.get("text_ok") is None and query_pages >= 2:
                            resp = {
                                "valid": False,
                                "ownership_confidence": float(top_score),
                                "tamper_suspected": True,
                                "method": "perceptual_pdf_ambiguous",
                                "note": "Perceptual match found, but the matched record is missing a stored text fingerprint (older upload). Re-upload the original file to upgrade verification.",
                                "candidates": [],
                            }
                            r = (top.get("row") or {})
                            resp["candidates"].append(
                                {
                                    "watermark_code": r.get("watermark_code"),
                                    "watermark_id": r.get("watermark_id"),
                                    "issued_at": r.get("issued_at").isoformat() if r.get("issued_at") else None,
                                    "owner": {"name": r.get("owner_name"), "email": r.get("owner_email")},
                                    "score": float(top.get("score", 0.0)),
                                    "dist_score": float(top.get("dist_score", 0.0)),
                                    "text_score": top.get("text_score"),
                                    "text_dist": top.get("text_dist"),
                                }
                            )
                            if debug_info is not None:
                                debug_info["method"] = "perceptual_pdf_ambiguous"
                                resp["debug"] = debug_info
                            return JSONResponse(resp)

                        # If the query has a text fingerprint but the top candidate explicitly mismatches,
                        # surface it as ambiguity/tamper instead of a generic failure.
                        if query_text_simhash and top.get("text_ok") is False and query_pages >= 2:
                            resp = {
                                "valid": False,
                                "ownership_confidence": float(top_score),
                                "tamper_suspected": True,
                                "method": "perceptual_pdf_ambiguous",
                                "note": "Strong visual similarity, but text fingerprint does not match. This often happens after exporting/resaving (e.g., Preview \"Save as PDF\") or content edits. Cannot confirm owner.",
                                "candidates": [],
                            }
                            r = (top.get("row") or {})
                            resp["candidates"].append(
                                {
                                    "watermark_code": r.get("watermark_code"),
                                    "watermark_id": r.get("watermark_id"),
                                    "issued_at": r.get("issued_at").isoformat() if r.get("issued_at") else None,
                                    "owner": {"name": r.get("owner_name"), "email": r.get("owner_email")},
                                    "score": float(top.get("score", 0.0)),
                                    "dist_score": float(top.get("dist_score", 0.0)),
                                    "text_score": top.get("text_score"),
                                    "text_dist": top.get("text_dist"),
                                }
                            )
                            if debug_info is not None:
                                debug_info["method"] = "perceptual_pdf_ambiguous"
                                resp["debug"] = debug_info
                            return JSONResponse(resp)

                        # Consider candidates that are essentially tied with the top one.
                        eps = 1e-6
                        tied = [
                            c
                            for c in pool
                            if abs(float(c.get("score", 0.0)) - top_score) <= eps
                            and abs(float(c.get("dist_score", 0.0)) - top_dist_score) <= eps
                        ]

                        # For 1-page PDFs, always treat any perceptual hit as ambiguous.
                        # Even if it looks unique, it's too easy to collide.
                        if query_pages <= 1:
                            tied = pool[:5]
                        if len(tied) > 1:
                            # Return top few candidates to allow the UI to explain ambiguity.
                            tied = tied[:5]
                            resp = {
                                "valid": False,
                                "ownership_confidence": float(top_score),
                                "tamper_suspected": True,
                                "method": "perceptual_pdf_ambiguous",
                                "note": "Perceptual match is not unique (or too little signal, e.g. a 1-page PDF). Cannot uniquely identify the owner.",
                                "candidates": [],
                            }

                            for c in tied:
                                r = c.get("row") or {}
                                resp["candidates"].append(
                                    {
                                        "watermark_code": r.get("watermark_code"),
                                        "watermark_id": r.get("watermark_id"),
                                        "issued_at": r.get("issued_at").isoformat() if r.get("issued_at") else None,
                                        "owner": {"name": r.get("owner_name"), "email": r.get("owner_email")},
                                        "score": float(c.get("score", 0.0)),
                                        "dist_score": float(c.get("dist_score", 0.0)),
                                        "text_score": c.get("text_score"),
                                        "text_dist": c.get("text_dist"),
                                    }
                                )

                            if debug_info is not None:
                                debug_info["method"] = "perceptual_pdf_ambiguous"
                                resp["debug"] = debug_info

                            return JSONResponse(resp)
                    except Exception:
                        pass

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
