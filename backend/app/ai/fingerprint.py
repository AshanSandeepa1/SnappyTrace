import cv2
import numpy as np


def dhash_bgr_image(bgr: np.ndarray, *, hash_size: int = 8) -> int:
    """Compute 64-bit dHash from a BGR image (OpenCV).

    dHash is simple and fast; it's not perfect for heavy crops, but works well for
    slight crops + recompression in small demos.
    """
    if bgr is None or bgr.size == 0:
        raise ValueError("empty image")

    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (hash_size + 1, hash_size), interpolation=cv2.INTER_AREA)
    diff = resized[:, 1:] > resized[:, :-1]

    bits = diff.flatten()
    value = 0
    for bit in bits:
        value = (value << 1) | int(bool(bit))
    return int(value)


def dhash_path(path: str, *, hash_size: int = 8) -> str:
    bgr = cv2.imread(path, cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError("could not read image")
    return f"{dhash_bgr_image(bgr, hash_size=hash_size):016x}"


def hamming_distance_hex64(a_hex: str, b_hex: str) -> int:
    a = int(a_hex, 16)
    b = int(b_hex, 16)
    return (a ^ b).bit_count()
