import base64
import hmac
import hashlib
from dataclasses import dataclass
from typing import Tuple

import cv2
import numpy as np
from reedsolo import RSCodec, ReedSolomonError


@dataclass(frozen=True)
class ExtractResult:
    ok: bool
    watermark_id_hex: str | None
    watermark_code: str | None
    confidence: float
    reason: str | None = None


_VERSION = 2
_ID_BYTES = 16
_TAG_BYTES = 16
_RSC_NSYM_V1 = 16  # parity bytes (legacy)
_RSC_NSYM_V2 = 32  # parity bytes (stronger ECC)


def _seed_from(secret: str, salt: str) -> int:
    digest = hashlib.sha256(_secret_bytes(secret) + b":" + salt.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big")


def _legacy_seed(secret: str) -> int:
    # Backward-compatible seed (older watermarks used sha256(secret) without any salt).
    return int.from_bytes(hashlib.sha256(_secret_bytes(secret)).digest()[:4], "big")


def _secret_bytes(secret: str) -> bytes:
    return secret.encode("utf-8")


def _watermark_code_from_hex(watermark_id_hex: str) -> str:
    return "WMK-" + watermark_id_hex[:12].upper()


def _pack_payload(watermark_id_hex: str, secret: str) -> bytes:
    raw_id = bytes.fromhex(watermark_id_hex)
    if len(raw_id) != _ID_BYTES:
        raise ValueError("watermark_id_hex must be 16 bytes (32 hex chars)")

    header = bytes([_VERSION]) + raw_id
    tag = hmac.new(_secret_bytes(secret), header, hashlib.sha256).digest()[:_TAG_BYTES]
    return header + tag


def _unpack_payload(payload: bytes, secret: str) -> Tuple[str, str]:
    if len(payload) != 1 + _ID_BYTES + _TAG_BYTES:
        raise ValueError("unexpected payload length")

    version = payload[0]
    if version not in (1, 2):
        raise ValueError("unsupported watermark version")

    raw_id = payload[1 : 1 + _ID_BYTES]
    tag = payload[1 + _ID_BYTES :]
    expected = hmac.new(_secret_bytes(secret), payload[: 1 + _ID_BYTES], hashlib.sha256).digest()[:_TAG_BYTES]
    if not hmac.compare_digest(tag, expected):
        raise ValueError("invalid watermark signature")

    watermark_id_hex = raw_id.hex()
    return watermark_id_hex, _watermark_code_from_hex(watermark_id_hex)


def _bytes_to_bits(data: bytes) -> np.ndarray:
    arr = np.frombuffer(data, dtype=np.uint8)
    return np.unpackbits(arr)


def _bits_to_bytes(bits: np.ndarray) -> bytes:
    packed = np.packbits(bits.astype(np.uint8))
    return packed.tobytes()


def _qim_embed(value: float, bit: int, delta: float) -> float:
    # Quantization Index Modulation: force coefficient into one of two quantization bins.
    q = 2.0 * delta
    base = np.round(value / q) * q
    return float(base + (delta if bit else 0.0))


def _qim_extract(value: float, delta: float) -> int:
    q = 2.0 * delta
    # Map to nearest bin and return 0/1 depending on offset.
    r = value - np.round(value / q) * q
    return 1 if r > (delta / 2.0) else 0


def embed_image_watermark(
    input_path: str,
    output_path: str,
    watermark_id_hex: str,
    secret: str,
    *,
    strength: float = 14.0,
    repeats: int = 8,
) -> None:
    """Embed a robust, server-verifiable watermark into an image.

    - Blind extraction on server (uses server secret; offline verify is not supported by design).
    - Redundant tiling (repeats) to improve crop resilience.
    """

    img = cv2.imread(input_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError("could not read image")

    has_alpha = img.ndim == 3 and img.shape[2] == 4

    if img.ndim == 2:
        bgr = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        alpha = None
    elif img.ndim == 3 and img.shape[2] in (3, 4):
        bgr = img[:, :, :3]
        alpha = img[:, :, 3] if has_alpha else None
    else:
        raise ValueError("unsupported image format")

    ycrcb = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)
    y = ycrcb[:, :, 0].astype(np.float32)

    # Prepare message (payload + RS parity)
    payload = _pack_payload(watermark_id_hex, secret)
    rsc = RSCodec(_RSC_NSYM_V2)
    encoded = bytes(rsc.encode(payload))
    bits = _bytes_to_bits(encoded)

    h, w = y.shape
    h8, w8 = (h // 8) * 8, (w // 8) * 8
    y_cropped = y[:h8, :w8]

    # Work on 8x8 blocks
    out = y_cropped.copy()

    # Multi-coefficient embedding improves robustness under recompression.
    # Avoid DC, use a few mid-frequencies.
    coeffs = [(3, 4), (4, 3), (2, 3)]

    def _embed_region(y_plane: np.ndarray, y0: int, x0: int, rh: int, rw: int, *, salt: str, region_repeats: int) -> None:
        region = y_plane[y0 : y0 + rh, x0 : x0 + rw]
        blocks_y = rh // 8
        blocks_x = rw // 8
        num_blocks = blocks_y * blocks_x
        if num_blocks <= 0:
            return

        # Lower repeats automatically if region is small.
        local_repeats = region_repeats
        if num_blocks < bits.size * local_repeats:
            local_repeats = max(1, num_blocks // max(1, bits.size))
        if local_repeats < 1:
            return

        seed = _seed_from(secret, salt)
        rng = np.random.default_rng(seed)
        perm = rng.permutation(num_blocks)
        total_positions = bits.size * local_repeats
        chosen = perm[:total_positions]

        idx = 0
        for _ in range(local_repeats):
            for bit in bits:
                block_index = int(chosen[idx])
                idx += 1
                by = (block_index // blocks_x) * 8
                bx = (block_index % blocks_x) * 8
                block = region[by : by + 8, bx : bx + 8]
                dct = cv2.dct(block)
                for uu, vv in coeffs:
                    original = float(dct[uu, vv])
                    dct[uu, vv] = _qim_embed(original, int(bit), strength)
                region[by : by + 8, bx : bx + 8] = cv2.idct(dct)

    # Crop-resilience strategy (v1): embed the same payload into multiple anchored regions.
    # This improves typical user crops (trimming edges / center crops) without heavy compute.
    min_dim = min(h8, w8)
    if min_dim < 64:
        raise ValueError("image too small to embed watermark")

    # IMPORTANT: region_size must be stable under slight crops.
    # If we derive it from image size, a small crop changes the region size,
    # which changes the block permutation length and breaks extraction.
    region_size = 256 if min_dim >= 256 else min_dim
    region_size = (region_size // 8) * 8
    if region_size < 64:
        region_size = min_dim

    anchors: list[tuple[str, int, int]] = []
    anchors.append(("tl", 0, 0))
    anchors.append(("tr", 0, max(0, w8 - region_size)))
    anchors.append(("bl", max(0, h8 - region_size), 0))
    anchors.append(("br", max(0, h8 - region_size), max(0, w8 - region_size)))
    anchors.append(("c", max(0, (h8 - region_size) // 2), max(0, (w8 - region_size) // 2)))

    # Deduplicate anchors if image is small.
    seen = set()
    unique: list[tuple[str, int, int]] = []
    for name, y0, x0 in anchors:
        key = (y0, x0)
        if key in seen:
            continue
        seen.add(key)
        unique.append((name, y0, x0))

    # Split repeats budget across regions to avoid over-distortion.
    region_repeats = max(1, int(np.ceil(repeats / max(1, len(unique)))))

    for name, y0, x0 in unique:
        _embed_region(out, y0, x0, region_size, region_size, salt=f"region:{name}", region_repeats=region_repeats)

    # Put back into image
    ycrcb_out = ycrcb.copy()
    y_full = ycrcb_out[:, :, 0].astype(np.float32)
    y_full[:h8, :w8] = np.clip(out, 0, 255)
    ycrcb_out[:, :, 0] = y_full.astype(np.uint8)

    bgr_out = cv2.cvtColor(ycrcb_out, cv2.COLOR_YCrCb2BGR)

    if alpha is not None:
        out_img = np.dstack([bgr_out, alpha])
    else:
        out_img = bgr_out

    # Save
    if output_path.lower().endswith(".jpg") or output_path.lower().endswith(".jpeg"):
        cv2.imwrite(output_path, out_img, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
    else:
        cv2.imwrite(output_path, out_img)


def extract_image_watermark(
    image_path: str,
    secret: str,
    *,
    strength: float = 10.0,
    repeats: int = 8,
    fast: bool = True,
) -> ExtractResult:
    img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        return ExtractResult(ok=False, watermark_id_hex=None, watermark_code=None, confidence=0.0, reason="could not read image")

    if img.ndim == 2:
        bgr = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    elif img.ndim == 3 and img.shape[2] in (3, 4):
        bgr = img[:, :, :3]
    else:
        return ExtractResult(ok=False, watermark_id_hex=None, watermark_code=None, confidence=0.0, reason="unsupported image format")

    ycrcb = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)
    y_full = ycrcb[:, :, 0].astype(np.float32)

    expected_payload_len = 1 + _ID_BYTES + _TAG_BYTES
    # Try both ECC sizes (v1/v2) unless we're in fast mode.
    # New embeds use v2; probing v1 adds CPU without helping current uploads.
    ecc_options = [(2, _RSC_NSYM_V2)] if fast else [(1, _RSC_NSYM_V1), (2, _RSC_NSYM_V2)]

    coeffs = [(3, 4), (4, 3), (2, 3)]

    # Cropping in Preview often shifts the origin by non-multiples of 8.
    # Full search over 64 offsets is very expensive; default to a fast path.
    if fast:
        offsets = [(0, 0)]
    else:
        offsets = [(dy, dx) for dy in range(8) for dx in range(8)]
        offsets.sort(key=lambda t: (t[0] + t[1], t[0], t[1]))

    def _decode_from_plane(y_plane: np.ndarray, *, seed: int, delta: float, repeats_hint: int, nsym: int) -> ExtractResult:
        best_fail: ExtractResult | None = None
        h, w = y_plane.shape
        if h < 32 or w < 32:
            return ExtractResult(ok=False, watermark_id_hex=None, watermark_code=None, confidence=0.0, reason="image too small")

        for dy, dx in offsets:
            yy = y_plane[dy:, dx:]
            hh, ww = yy.shape
            h8, w8 = (hh // 8) * 8, (ww // 8) * 8
            if h8 < 64 or w8 < 64:
                continue
            y = yy[:h8, :w8]

            blocks_y = h8 // 8
            blocks_x = w8 // 8
            num_blocks = blocks_y * blocks_x
            rsc = RSCodec(nsym)
            expected_encoded_len = expected_payload_len + nsym
            expected_bits = expected_encoded_len * 8

            # We only need enough blocks for one full payload. Repeats are handled below.
            if num_blocks < expected_bits:
                continue

            local_repeats = max(1, int(repeats_hint))
            total_positions = expected_bits * local_repeats
            if num_blocks < total_positions:
                local_repeats = max(1, num_blocks // expected_bits)
                total_positions = expected_bits * local_repeats

            rng = np.random.default_rng(seed)
            # Avoid generating a full permutation of *all* blocks for large images.
            # In fast mode we prefer speed; sampling with replacement is acceptable.
            if fast and num_blocks > (total_positions * 8):
                chosen = rng.integers(0, num_blocks, size=total_positions, dtype=np.int64)
            else:
                perm = rng.permutation(num_blocks)
                chosen = perm[:total_positions]
            votes = np.zeros((expected_bits, 2), dtype=np.int32)
            idx = 0
            for _ in range(local_repeats):
                for i in range(expected_bits):
                    block_index = int(chosen[idx])
                    idx += 1
                    by = (block_index // blocks_x) * 8
                    bx = (block_index % blocks_x) * 8
                    block = y[by : by + 8, bx : bx + 8]
                    dct = cv2.dct(block)
                    # Majority vote across multiple coefficients
                    ones = 0
                    for uu, vv in coeffs:
                        ones += _qim_extract(float(dct[uu, vv]), delta)
                    bit = 1 if ones >= (len(coeffs) // 2 + 1) else 0
                    votes[i, bit] += 1

            decided = (votes[:, 1] > votes[:, 0]).astype(np.uint8)
            margins = np.abs(votes[:, 1] - votes[:, 0]) / max(1, local_repeats)
            confidence = float(np.clip(np.mean(margins), 0.0, 1.0))

            data = _bits_to_bytes(decided)
            try:
                decoded = bytes(rsc.decode(bytearray(data))[0])
                watermark_id_hex, watermark_code = _unpack_payload(decoded, secret)
                return ExtractResult(ok=True, watermark_id_hex=watermark_id_hex, watermark_code=watermark_code, confidence=confidence)
            except (ReedSolomonError, ValueError):
                fail = ExtractResult(ok=False, watermark_id_hex=None, watermark_code=None, confidence=confidence, reason="watermark decode failed")
                if best_fail is None or fail.confidence > best_fail.confidence:
                    best_fail = fail

        return best_fail or ExtractResult(ok=False, watermark_id_hex=None, watermark_code=None, confidence=0.0, reason="watermark decode failed")

    # Strength sweep to tolerate JPEG/resize variance.
    if fast:
        deltas = [14.0, 16.0, float(strength)]
        repeat_hints = [2, 1]
    else:
        deltas = [float(strength), 12.0, 14.0, 16.0, 18.0]
        repeat_hints = [max(1, repeats), max(1, repeats // 2), 1]

    deltas = list(dict.fromkeys([float(d) for d in deltas]))
    repeat_hints = list(dict.fromkeys([int(r) for r in repeat_hints if int(r) >= 1]))

    best_fail: ExtractResult | None = None

    # Decode strategy:
    # - Fast mode: try region-based first (current embed) and skip legacy sweep.
    # - Slow mode: try legacy first for backwards compatibility.

    # 1) Region-based scheme (current uploads)
    h, w = y_full.shape
    h8, w8 = (h // 8) * 8, (w // 8) * 8
    min_dim = min(h8, w8)
    if fast:
        region_sizes = [256]
        if min_dim < 256:
            region_sizes = [max(64, (min_dim // 8) * 8)]
    else:
        # Try a few region sizes so slight crops don't break decoding.
        region_sizes = [256, 320, 384, 512]
        if min_dim < 256:
            region_sizes.append(max(64, (min_dim // 8) * 8))
        region_sizes = [rs for rs in region_sizes if rs >= 64 and rs <= min_dim]
        region_sizes = list(dict.fromkeys(region_sizes))

    anchors = [
        ("c", lambda rs: (max(0, (h8 - rs) // 2), max(0, (w8 - rs) // 2))),
        ("tl", lambda rs: (0, 0)),
    ] if fast else [
        ("tl", lambda rs: (0, 0)),
        ("tr", lambda rs: (0, max(0, w8 - rs))),
        ("bl", lambda rs: (max(0, h8 - rs), 0)),
        ("br", lambda rs: (max(0, h8 - rs), max(0, w8 - rs))),
        ("c", lambda rs: (max(0, (h8 - rs) // 2), max(0, (w8 - rs) // 2))),
    ]

    for delta in deltas:
        for rs in region_sizes:
            for name, pos_fn in anchors:
                y0, x0 = pos_fn(rs)
                region = y_full[y0 : y0 + rs, x0 : x0 + rs]
                seed = _seed_from(secret, f"region:{name}")
                for _ver, nsym in ecc_options:
                    # Try a couple repeat hints; region embedding may have 1-2 repeats.
                    for rh in (2, 1):
                        res = _decode_from_plane(region, seed=seed, delta=delta, repeats_hint=rh, nsym=nsym)
                        if res.ok:
                            return res
                        best_fail = res if best_fail is None or res.confidence > best_fail.confidence else best_fail

    # 2) Legacy whole-image scheme (older uploads)
    if not fast:
        legacy_seed = _legacy_seed(secret)
        for delta in deltas:
            for rh in repeat_hints:
                for _ver, nsym in ecc_options:
                    res = _decode_from_plane(y_full, seed=legacy_seed, delta=delta, repeats_hint=rh, nsym=nsym)
                    if res.ok:
                        return res
                    best_fail = res if best_fail is None or res.confidence > best_fail.confidence else best_fail

    confidence = float((best_fail.confidence if best_fail is not None else 0.0) or 0.0)
    return ExtractResult(
        ok=False,
        watermark_id_hex=None,
        watermark_code=None,
        confidence=confidence,
        reason="watermark not detected (file may be original or heavily altered)",
    )
