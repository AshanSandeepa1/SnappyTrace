# app/routes/upload.py

import os, shutil, json, hashlib
from uuid import uuid4
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.auth.jwt import get_current_user
from app.ai.embed import embed_watermark_ai
from app.ai.fingerprint import dhash_path
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

        # Embed watermark (Phase 1: images)
        watermarked_path, watermark_id, watermark_code = embed_watermark_ai(
            temp_path, str(user["id"]), metadata
        )

        perceptual_hash = None
        try:
            perceptual_hash = dhash_path(watermarked_path)
        except Exception:
            perceptual_hash = None

        # Save in DB
        await db.execute(
            """
            INSERT INTO watermarked_files (
                id, user_id, original_filename,
                file_hash,
                mime_type, original_file_hash,
                watermark_id, watermark_code,
                perceptual_hash,
                metadata, metadata_hash, source_created_at,
                issued_at
            )
            VALUES (
                $1, $2, $3,
                $4,
                $5, $6,
                $7, $8,
                $9,
                $10::jsonb, $11, $12
                , now()
            )
            """,
            *(
                str(uuid4()),
                str(user["id"]),
                file.filename,
                file_hash,
                file.content_type,
                file_hash,
                watermark_id,
                watermark_code,
                perceptual_hash,
                json.dumps(metadata),
                metadata_hash,
                datetime.fromisoformat(createdDate).date(),
            ),
        )


        return JSONResponse({
            "message": "File successfully watermarked.",
            "watermark_id": watermark_id,
            "watermark_code": watermark_code,
            "original_filename": file.filename,
            "download_url": str(request.base_url) + f"files/{os.path.basename(watermarked_path)}"
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
