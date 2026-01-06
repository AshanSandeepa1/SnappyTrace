from fastapi import APIRouter, Depends

from app.auth.jwt import get_current_user
from app.database import db

router = APIRouter()


@router.get("/my-files")
async def my_files(user=Depends(get_current_user)):
    rows = []
    # asyncpg returns Record; convert minimal fields
    result = await db.fetch_all(
        """
        SELECT watermark_code, watermark_id, original_filename, mime_type, original_file_hash,
               metadata, metadata_hash, source_created_at, issued_at
        FROM watermarked_files
        WHERE user_id=$1
        ORDER BY issued_at DESC NULLS LAST, source_created_at DESC NULLS LAST
        LIMIT 50
        """,
        str(user["id"]),
    )
    for r in result:
        rows.append(
            {
                "watermark_code": r["watermark_code"],
                "watermark_id": r["watermark_id"],
                "original_filename": r["original_filename"],
                "mime_type": r["mime_type"],
                "original_file_hash": r["original_file_hash"],
                "metadata": r["metadata"],
                "metadata_hash": r["metadata_hash"],
                "source_created_at": r["source_created_at"].isoformat() if r["source_created_at"] else None,
                "issued_at": r["issued_at"].isoformat() if r["issued_at"] else None,
            }
        )

    return {"items": rows}
