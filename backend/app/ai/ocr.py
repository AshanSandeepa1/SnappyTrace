from typing import List, Optional
import fitz
from PIL import Image
import io
import pytesseract


def _render_page_to_pil(page, dpi: int = 150) -> Image.Image:
    mat = fitz.Matrix(dpi / 72.0, dpi / 72.0)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return img


def extract_text_from_pdf(path: str, dpi: int = 150, max_pages: Optional[int] = 10) -> List[str]:
    """Render PDF pages and run Tesseract OCR, returning a list of page strings.

    Keeps a simple limit via `max_pages` for performance.
    """
    texts = []
    doc = fitz.open(path)
    try:
        total = min(len(doc), max_pages or len(doc))
        for i in range(total):
            page = doc.load_page(i)
            try:
                img = _render_page_to_pil(page, dpi=dpi)
                txt = pytesseract.image_to_string(img)
                texts.append(txt)
            except Exception:
                texts.append("")
    finally:
        doc.close()
    return texts
