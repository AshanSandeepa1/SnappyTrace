import os

from fastapi import APIRouter, Depends, Request

from app.auth.jwt import get_current_user
from app.database import db

router = APIRouter()


_TMP_STORAGE_DIR = "/tmp/snappy_uploads"


@router.get("/my-files")
async def my_files(request: Request, user=Depends(get_current_user)):
    rows = []
    # asyncpg returns Record; convert minimal fields
    result = await db.fetch_all(
        """
        SELECT watermark_code, watermark_id, original_filename, stored_filename, mime_type, original_file_hash,
               metadata, metadata_hash, source_created_at, issued_at
        FROM watermarked_files
        WHERE user_id=$1
        ORDER BY issued_at DESC NULLS LAST, source_created_at DESC NULLS LAST
        LIMIT 50
        """,
        str(user["id"]),
    )
    for r in result:
        stored_filename = r["stored_filename"]
        download_available = False
        if stored_filename:
            # Files are served from a tmp dir inside the container. After a container restart,
            # the DB record can remain but the underlying file may be gone.
            download_available = os.path.exists(
                os.path.join(_TMP_STORAGE_DIR, stored_filename)
            )

        download_url = (
            str(request.base_url) + f"files/{stored_filename}"
            if stored_filename and download_available
            else None
        )
        rows.append(
            {
                "watermark_code": r["watermark_code"],
                "watermark_id": r["watermark_id"],
                "original_filename": r["original_filename"],
                "stored_filename": stored_filename,
                "download_url": download_url,
                "download_available": download_available,
                "mime_type": r["mime_type"],
                "original_file_hash": r["original_file_hash"],
                "metadata": r["metadata"],
                "metadata_hash": r["metadata_hash"],
                "source_created_at": r["source_created_at"].isoformat() if r["source_created_at"] else None,
                "issued_at": r["issued_at"].isoformat() if r["issued_at"] else None,
            }
        )

    return {"items": rows}
