# app/routes/upload.py

import shutil, os, hashlib, json
from uuid import uuid4
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
        # Save uploaded file to temp
        filename = f"{uuid4().hex}_{file.filename}"
        temp_path = os.path.join(UPLOAD_DIR, filename)
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Calculate hash
        file_hash = compute_sha256(temp_path)

        # Collect metadata
        metadata = {
            "title": title,
            "author": author,
            "createdDate": createdDate,
            "organization": organization
        }

        # Apply watermark (placeholder AI function)
        watermarked_path, watermark_id = embed_watermark_ai(temp_path, user["sub"], metadata)

        # Store in database
        await db.execute("""
            INSERT INTO watermarked_files (
              id, user_id, original_filename, file_hash,
              watermark_id, metadata, watermarked_path
            )
            VALUES (
              :id, :user_id, :original_filename, :file_hash,
              :watermark_id, :metadata, :watermarked_path
            )
        """, {
            "id": str(uuid4()),
            "user_id": user["sub"],
            "original_filename": file.filename,
            "file_hash": file_hash,
            "watermark_id": watermark_id,
            "metadata": json.dumps(metadata),
            "watermarked_path": watermarked_path
        })

        return JSONResponse({
            "message": "File successfully watermarked.",
            "watermark_id": watermark_id,
            "original_filename": file.filename
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
