# app/routes/upload.py

import os, shutil, json, hashlib
from uuid import uuid4
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.auth.jwt import get_current_user
from app.ai.embed import embed_watermark_ai
from app.database import db

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

        # AI embed
        watermarked_path, watermark_id = embed_watermark_ai(temp_path, str(user["id"]), metadata)

        # Save in DB
        await db.execute("""
            INSERT INTO watermarked_files (
            id, user_id, original_filename, file_hash,
            watermark_id, metadata, created_at, watermarked_path
            )
            VALUES (
            $1, $2, $3, $4,
            $5, $6, $7, $8
            )
        """, *(
            str(uuid4()),
            str(user["id"]),
            file.filename,
            file_hash,
            watermark_id,
            json.dumps(metadata),
            datetime.fromisoformat(createdDate),
            watermarked_path
        ))


        return JSONResponse({
            "message": "File successfully watermarked.",
            "watermark_id": watermark_id,
            "original_filename": file.filename,
            "download_url": f"http://localhost:8000/files/{os.path.basename(watermarked_path)}"
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
