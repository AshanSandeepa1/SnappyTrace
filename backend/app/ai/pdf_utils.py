import hashlib
import json
from typing import List, Tuple, Optional

import fitz
import numpy as np
from PIL import Image

from app.ai.fingerprint import dhash_bgr_image
from app.config import SECRET_KEY


def canonicalize_pdf_text_xmp(pdf_path: str) -> bytes:
    """Extract PDF text (page order) and metadata, return deterministic bytes."""
    doc = fitz.open(pdf_path)
    parts = []
    for page in doc:
        text = page.get_text("text") or ""
        parts.append(text.strip())

    # Use document metadata as a stable JSON object
    meta = doc.metadata or {}
    try:
        meta_json = json.dumps(meta, sort_keys=True, separators=(',', ':'))
    except Exception:
        meta_json = json.dumps({k: str(v) for k, v in meta.items()}, sort_keys=True, separators=(',', ':'))

    payload = "\n".join(parts) + "\n" + meta_json
    return payload.encode("utf-8")


def compute_canonical_hash(pdf_path: str) -> str:
    data = canonicalize_pdf_text_xmp(pdf_path)
    return hashlib.sha256(data).hexdigest()


def compute_canonical_hmac(pdf_path: str, secret: str = SECRET_KEY) -> str:
    import hmac
    data = canonicalize_pdf_text_xmp(pdf_path)
    return hmac.new(secret.encode("utf-8"), data, hashlib.sha256).hexdigest()


def _pixmap_to_bgr_array(pix) -> np.ndarray:
    mode = pix.n
    arr = np.frombuffer(pix.samples, dtype=np.uint8)
    if mode == 1:
        arr = arr.reshape((pix.height, pix.width))
        rgb = np.stack([arr, arr, arr], axis=-1)
    else:
        arr = arr.reshape((pix.height, pix.width, pix.n))
        # PyMuPDF returns samples in RGB(A)
        rgb = arr[:, :, :3]

    # Convert RGB -> BGR for OpenCV compatibility
    bgr = rgb[:, :, ::-1]
    return bgr


def rasterize_pages_and_hashes(pdf_path: str, dpi: int = 150, max_pages: Optional[int] = None) -> List[str]:
    """Render pages deterministically and compute dHash hex strings per page."""
    doc = fitz.open(pdf_path)
    hashes = []
    total = len(doc)
    if max_pages is not None:
        total = min(total, max_pages)

    mat = fitz.Matrix(dpi / 72.0, dpi / 72.0)
    for i in range(total):
        page = doc[i]
        pix = page.get_pixmap(matrix=mat, alpha=False)
        bgr = _pixmap_to_bgr_array(pix)
        h = dhash_bgr_image(bgr)
        hashes.append(f"{h:016x}")

    return hashes


def render_page_thumbnail(pdf_path: str, page_number: int, dpi: int = 150, max_side: int = 512) -> Image.Image:
    doc = fitz.open(pdf_path)
    page = doc[page_number]
    mat = fitz.Matrix(dpi / 72.0, dpi / 72.0)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    bgr = _pixmap_to_bgr_array(pix)
    # Convert BGR -> RGB for PIL
    rgb = bgr[:, :, ::-1]
    img = Image.fromarray(rgb)
    img.thumbnail((max_side, max_side), Image.LANCZOS)
    return img
