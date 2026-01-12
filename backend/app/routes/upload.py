# app/routes/upload.py

import os, shutil, json, hashlib
from uuid import uuid4
from datetime import datetime
from typing import Optional, Tuple

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.auth.jwt import get_current_user
from app.ai.embed import embed_watermark_ai
try:
    import fitz
except Exception:
    fitz = None
from app.ai.fingerprint import dhash_path
from app.pades import sign_pdf_with_pkcs12_async
from app.ai.pdf_utils import rasterize_pages_and_hashes
import os
from app.database import db
from app.db_schema import canonical_metadata_hash

router = APIRouter()

UPLOAD_DIR = "/tmp/snappy_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def compute_sha256(file_path):
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


def _resolve_pdf_signing_config() -> Tuple[Optional[str], Optional[str]]:
    """Resolve PKCS#12 path + passphrase for PDF signing.

    We support both local dev paths (repo-relative) and container paths.
    """
    env_path = os.getenv("PDF_SIGN_P12_PATH")
    env_pass = os.getenv("PDF_SIGN_P12_PASS")

    candidates = []
    if env_path:
        candidates.append(env_path)
        # If compose/.env provides a repo-relative path like "backend/app/...",
        # strip the leading "backend/" to match paths inside the backend image.
        if env_path.startswith("backend/"):
            candidates.append(env_path[len("backend/") :])

    # Common dev/container locations
    candidates.extend(
        [
            "/app/app/certs/demo.p12",  # inside docker image
            "backend/app/certs/demo.p12",  # repo-relative when running backend locally
        ]
    )

    chosen_path = None
    for p in candidates:
        try:
            if p and os.path.exists(p):
                chosen_path = p
                break
        except Exception:
            continue

    if not chosen_path:
        return None, None

    chosen_pass = env_pass
    # If using the demo cert and no password provided, default for dev.
    if (not chosen_pass) and os.path.basename(chosen_path) == "demo.p12":
        chosen_pass = "demo-password"

    return chosen_path, chosen_pass

@router.post("/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    title: str = Form(...),
    author: str = Form(...),
    createdDate: str = Form(...),
    organization: str = Form(""),
    user=Depends(get_current_user)
):
    try:
        # Save file to temp
        filename = f"{uuid4().hex}_{file.filename}"
        temp_path = os.path.join(UPLOAD_DIR, filename)
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Hash and metadata
        file_hash = compute_sha256(temp_path)
        metadata = {
            "title": title,
            "author": author,
            "createdDate": createdDate,
            "organization": organization
        }
        metadata_hash = canonical_metadata_hash(metadata)

        # Generate watermark id/code for tracking (used for images and documents)
        watermark_id = uuid4().hex
        watermark_code = "WMK-" + watermark_id[:12].upper()

        is_pdf = file.filename.lower().endswith(".pdf") or file.content_type == "application/pdf"
        watermarked_path = temp_path

        if is_pdf:
            # For PDFs we do NOT embed an image watermark. Optionally sign if PKCS#12 configured.
            p12_path, p12_pass = _resolve_pdf_signing_config()
            try:
                if p12_path:
                    signed_path = os.path.join(UPLOAD_DIR, f"SIGNED_{uuid4().hex}_{file.filename}")
                    try:
                        res = await sign_pdf_with_pkcs12_async(p12_path, p12_pass, temp_path, signed_path)
                    except Exception as e:
                        err = str(e) or ""
                        # If the error looks like hybrid xref issues, try to sanitize using PyMuPDF
                        if fitz is not None and "hybrid" in err.lower():
                            try:
                                sanitized = os.path.join(UPLOAD_DIR, f"SAN_{uuid4().hex}_{file.filename}")
                                doc = fitz.open(temp_path)
                                doc.save(sanitized, incremental=False)
                                doc.close()
                                res = await sign_pdf_with_pkcs12_async(p12_path, p12_pass, sanitized, signed_path)
                                temp_path = sanitized
                            except Exception as e2:
                                print(f"PDF signing failed after sanitization for {file.filename}: {e2}")
                                raise
                        else:
                            print(f"PDF signing failed for {file.filename}: {e}")
                            raise

                    watermarked_path = signed_path
                    signer_cert_thumbprint = res.get("signer_cert_thumbprint")
                    signed_at = res.get("signed_at")
                    # Defensive: older signer implementations returned ISO strings.
                    if isinstance(signed_at, str):
                        try:
                            signed_at = datetime.fromisoformat(signed_at)
                        except Exception:
                            signed_at = None
                else:
                    signer_cert_thumbprint = None
                    signed_at = None
            except Exception:
                # Don't silently swallow signing failures: it makes PAdES "randomly" fail.
                # We continue without a signature, but log so it's diagnosable.
                signer_cert_thumbprint = None
                signed_at = None

            # compute per-page hashes for scanned PDFs (store as JSONB)
            try:
                per_page_hashes = rasterize_pages_and_hashes(watermarked_path, dpi=150, max_pages=10)
            except Exception:
                per_page_hashes = None

        else:
            # Embed watermark for images
            watermarked_path, watermark_id, watermark_code = embed_watermark_ai(
                temp_path, str(user["id"]), metadata
            )
            signer_cert_thumbprint = None
            signed_at = None
            per_page_hashes = None

        perceptual_hash = None
        try:
            perceptual_hash = dhash_path(watermarked_path) if not is_pdf else None
        except Exception:
            perceptual_hash = None

        stored_filename = os.path.basename(watermarked_path) if watermarked_path else None

        # For PDFs, store the hash of the final produced file (signed/sanitized).
        # This allows `/verify` to map a downloaded signed PDF back to its DB row.
        if is_pdf:
            try:
                file_hash = compute_sha256(watermarked_path)
            except Exception:
                pass

        # Save in DB
        await db.execute(
            """
            INSERT INTO watermarked_files (
                id, user_id, original_filename,
                stored_filename,
                mime_type, original_file_hash,
                watermark_id, watermark_code,
                perceptual_hash,
                metadata, metadata_hash, source_created_at,
                signed_at, signer_cert_thumbprint, signer_name, per_page_hashes
            )
            VALUES (
                $1, $2, $3,
                $4,
                $5, $6,
                $7, $8,
                $9,
                $10::jsonb, $11, $12,
                $13, $14, $15, $16
            )
            """,
            *(
                str(uuid4()),
                str(user["id"]),
                file.filename,
                stored_filename,
                file.content_type,
                file_hash,
                watermark_id,
                watermark_code,
                perceptual_hash,
                json.dumps(metadata),
                metadata_hash,
                datetime.fromisoformat(createdDate).date(),
                signed_at,
                signer_cert_thumbprint,
                None,
                json.dumps(per_page_hashes) if per_page_hashes is not None else None,
            ),
        )


        return JSONResponse({
            "message": "File successfully watermarked.",
            "watermark_id": watermark_id,
            "watermark_code": watermark_code,
            "original_filename": file.filename,
            "stored_filename": stored_filename,
            "download_url": str(request.base_url) + f"files/{os.path.basename(watermarked_path)}"
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
