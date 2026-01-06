import os
import shutil
import json
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


@router.post("/verify")
async def verify_file(file: UploadFile = File(...)):
    """Verify a watermark by extracting it from an uploaded file."""
    filename = f"verify_{uuid4().hex}_{file.filename}"
    temp_path = os.path.join(UPLOAD_DIR, filename)
    extracted = None

    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

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
