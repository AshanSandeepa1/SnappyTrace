# app/ai/embed.py
import mimetypes
import os
from uuid import uuid4

from app.config import SECRET_KEY
from app.ai.image_watermark import embed_image_watermark, extract_image_watermark


def _is_image(path: str) -> bool:
    mt, _ = mimetypes.guess_type(path)
    return bool(mt and mt.startswith("image/"))


def _watermark_code_from_hex(watermark_id_hex: str) -> str:
    return "WMK-" + watermark_id_hex[:12].upper()


def embed_watermark_ai(file_path: str, user_id: str, metadata: dict):
    """Embed a watermark into a file.

    Phase 1: supports images only (JPG/PNG). Video/docs will be added later.
    Returns (watermarked_path, watermark_id_hex, watermark_code).
    """

    if not _is_image(file_path):
        raise ValueError("Phase-1 supports images only")

    watermark_id_hex = uuid4().hex  # 32 hex chars / 16 bytes
    watermark_code = _watermark_code_from_hex(watermark_id_hex)

    # Best output choice: keep PNG if input is PNG (supports transparency), otherwise use JPEG.
    ext = os.path.splitext(file_path)[1].lower()
    output_ext = ".png" if ext == ".png" else ".jpg"

    output_path = os.path.join(os.path.dirname(file_path), f"{watermark_code}{output_ext}")
    embed_image_watermark(
        input_path=file_path,
        output_path=output_path,
        watermark_id_hex=watermark_id_hex,
        secret=SECRET_KEY,
    )

    return output_path, watermark_id_hex, watermark_code


def extract_watermark_ai(file_path: str) -> dict:
    """Extract and verify a watermark from a file."""

    if not _is_image(file_path):
        return {
            "valid": False,
            "reason": "Phase-1 supports images only",
            "confidence": 0.0,
        }

    extracted = extract_image_watermark(file_path, secret=SECRET_KEY, fast=True)
    if not extracted.ok:
        return {
            "valid": False,
            "reason": extracted.reason or "watermark not found",
            "confidence": extracted.confidence,
        }

    return {
        "valid": True,
        "watermark_id": extracted.watermark_id_hex,
        "watermark_code": extracted.watermark_code,
        "confidence": extracted.confidence,
    }
