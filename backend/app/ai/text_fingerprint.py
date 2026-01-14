import hashlib
import re
from collections import Counter
from typing import Optional


_WORD_RE = re.compile(r"[a-z0-9]{2,}")


def simhash64_hex(text: str) -> Optional[str]:
    """Compute a 64-bit SimHash of text, returned as 16-hex chars.

    This is a lightweight local fingerprint (no external services).
    It is robust to minor OCR noise and formatting changes.

    Returns None if text is empty/too small.
    """
    if not text:
        return None

    tokens = _WORD_RE.findall(text.lower())
    if len(tokens) < 10:
        return None

    counts = Counter(tokens)
    vec = [0] * 64

    for token, weight in counts.items():
        # Stable 64-bit token hash (MD5 is fine here; we're not using it for security).
        digest = hashlib.md5(token.encode("utf-8")).digest()  # noqa: S324
        h64 = int.from_bytes(digest[:8], "big", signed=False)
        for i in range(64):
            bit = (h64 >> i) & 1
            vec[i] += weight if bit else -weight

    fp = 0
    for i, v in enumerate(vec):
        if v > 0:
            fp |= 1 << i

    return f"{fp:016x}"
