import hashlib
import asyncio
import os
from datetime import datetime
from typing import Optional

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12

try:
    from pyhanko.sign import signers
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
    from pyhanko.pdf_utils.reader import PdfFileReader
    from pyhanko.sign.validation import validate_pdf_signature
    from pyhanko.sign.validation import async_validate_pdf_signature
    from pyhanko_certvalidator import ValidationContext
except Exception:
    # pyhanko may be missing in some dev environments; raise on use
    signers = None
    IncrementalPdfFileWriter = None
    PdfFileReader = None
    validate_pdf_signature = None
    async_validate_pdf_signature = None
    ValidationContext = None


def _thumbprint_from_cert(cert) -> str:
    der = cert.public_bytes(serialization.Encoding.DER)
    return hashlib.sha256(der).hexdigest()


def load_pkcs12_thumbprint(p12_path: str, p12_pass: Optional[str]) -> str:
    """Load a PKCS#12 and return the certificate SHA-256 thumbprint."""
    with open(p12_path, "rb") as f:
        data = f.read()
    key, cert, add_certs = pkcs12.load_key_and_certificates(data, p12_pass.encode() if p12_pass else None)
    if cert is None:
        raise ValueError("PKCS12 does not contain a certificate")
    return _thumbprint_from_cert(cert)


def sign_pdf_with_pkcs12(p12_path: str, p12_pass: Optional[str], in_path: str, out_path: str) -> dict:
    """
    Sign `in_path` producing `out_path` using PKCS#12 keystore.
    Returns dict with `signer_cert_thumbprint` and `signed_at`.
    """
    # NOTE: In newer pyHanko versions, PdfSigner.sign_pdf() may call asyncio.run()
    # internally, which cannot be used inside FastAPI's running event loop.
    # Use the async helper in async contexts.
    try:
        asyncio.get_running_loop()
        raise RuntimeError(
            "sign_pdf_with_pkcs12() cannot be called from a running event loop; "
            "use await sign_pdf_with_pkcs12_async() instead"
        )
    except RuntimeError as e:
        # If there is no running loop, get_running_loop() raises RuntimeError.
        # But we also raise RuntimeError above with our own message; distinguish them.
        if str(e).startswith("sign_pdf_with_pkcs12() cannot"):
            raise

    return asyncio.run(sign_pdf_with_pkcs12_async(p12_path, p12_pass, in_path, out_path))


def _resolve_default_p12_config() -> tuple[Optional[str], Optional[str]]:
    """Resolve a default PKCS#12 path/passphrase from environment and common locations."""
    p12_path = os.getenv("PDF_SIGN_P12_PATH")
    p12_pass = os.getenv("PDF_SIGN_P12_PASS")

    if p12_path and os.path.exists(p12_path):
        return p12_path, p12_pass

    # Common in-container repo layout: /app/app/certs/demo.p12
    candidate = os.path.join(os.path.dirname(__file__), "certs", "demo.p12")
    if os.path.exists(candidate):
        return candidate, p12_pass

    return None, p12_pass


def _build_validation_context() -> Optional["ValidationContext"]:
    """Build a ValidationContext for signature validation.

    If the backend is configured with a signing PKCS#12 (demo cert), treat it as
    a trust root. This avoids noisy self-signed path-building errors in logs.
    """
    if ValidationContext is None:
        return None

    p12_path, p12_pass = _resolve_default_p12_config()
    if signers is not None and p12_path and os.path.exists(p12_path):
        try:
            signer = signers.SimpleSigner.load_pkcs12(
                p12_path,
                passphrase=p12_pass.encode("utf-8") if p12_pass else None,
            )
            signing_cert = getattr(signer, "signing_cert", None)
            if signing_cert is not None:
                return ValidationContext(trust_roots=[signing_cert], allow_fetching=False)
        except Exception:
            pass

    # Default: no trust roots. We'll still validate cryptographic integrity.
    try:
        return ValidationContext(allow_fetching=False)
    except Exception:
        return None


async def sign_pdf_with_pkcs12_async(
    p12_path: str, p12_pass: Optional[str], in_path: str, out_path: str
) -> dict:
    """Async PAdES signing helper (safe to call from FastAPI endpoints)."""
    if signers is None:
        raise RuntimeError("pyhanko is not available")

    signer = signers.SimpleSigner.load_pkcs12(
        p12_path,
        passphrase=p12_pass.encode("utf-8") if p12_pass else None,
    )
    if signer is None:
        raise FileNotFoundError(f"Could not load PKCS#12 from '{p12_path}'")

    meta = signers.PdfSignatureMetadata(field_name="Signature1")
    pdf_signer = signers.PdfSigner(meta, signer=signer)

    with open(in_path, "rb") as inf:
        w = IncrementalPdfFileWriter(inf)
        with open(out_path, "wb") as outf:
            async_sign = getattr(pdf_signer, "async_sign_pdf", None)
            if callable(async_sign):
                await async_sign(w, output=outf)
            else:
                pdf_signer.sign_pdf(w, output=outf)

    # Extract thumbprint from PKCS#12 in a robust way
    with open(p12_path, "rb") as f:
        data = f.read()
    key, cert, add_certs = pkcs12.load_key_and_certificates(
        data, p12_pass.encode() if p12_pass else None
    )
    thumb = _thumbprint_from_cert(cert)
    return {"signer_cert_thumbprint": thumb, "signed_at": datetime.utcnow()}


def verify_pdf_signature(pdf_path: str) -> dict:
    """Synchronous wrapper around :func:`verify_pdf_signature_async`.

    In pyHanko 0.9+, signature validation has an async API. In an async context
    (FastAPI request), call and await :func:`verify_pdf_signature_async` instead.
    """
    try:
        asyncio.get_running_loop()
        raise RuntimeError(
            "verify_pdf_signature() cannot be called from a running event loop; "
            "use await verify_pdf_signature_async() instead"
        )
    except RuntimeError as e:
        if str(e).startswith("verify_pdf_signature() cannot"):
            raise

    return asyncio.run(verify_pdf_signature_async(pdf_path))


async def verify_pdf_signature_async(pdf_path: str) -> dict:
    """Verify signatures on a PDF (async).

    Returns a dict:
      {valid: bool, signer_cert_thumbprint: Optional[str], signer_name: Optional[str], details: ...}
    """
    result = {"valid": False, "signer_cert_thumbprint": None, "signer_name": None, "details": None}

    # Always do a quick heuristic check for embedded signature markers.
    try:
        with open(pdf_path, "rb") as f:
            blob = f.read()
        has_byte_range = b"/ByteRange" in blob
    except Exception as e:
        result["details"] = str(e)
        return result

    if validate_pdf_signature is None or PdfFileReader is None:
        result["details"] = "signature-like contents present" if has_byte_range else "no signature found"
        return result

    if not has_byte_range:
        result["details"] = "no signature found"
        return result

    try:
        # We primarily care about cryptographic integrity here; trust can be enforced separately.
        # However, trusting our configured demo signing cert avoids noisy self-signed warnings.
        vc = _build_validation_context()

        sigs = []
        all_good = True

        # Keep the file handle open while validating; embedded signature objects
        # may read/seek on the underlying stream.
        with open(pdf_path, "rb") as f:
            r = PdfFileReader(f)
            embedded = list(getattr(r, "embedded_signatures", []) or [])

            if not embedded:
                result["details"] = "no embedded signatures"
                return result

            for emb in embedded:
                try:
                    # In pyHanko 0.9+, the underlying validator is async.
                    if async_validate_pdf_signature is not None:
                        status = await async_validate_pdf_signature(
                            emb, signer_validation_context=vc
                        )
                    else:
                        status = validate_pdf_signature(emb, signer_validation_context=vc)
                        if asyncio.iscoroutine(status):
                            status = await status
                    intact = bool(getattr(status, "intact", False))
                    valid = bool(getattr(status, "valid", False))
                    trusted = bool(getattr(status, "trusted", False))
                    all_good = all_good and intact and valid

                    # pyHanko exposes the signer's end-entity cert as `signer_cert`
                    signing_cert = getattr(emb, "signer_cert", None)
                    thumb = None
                    name = None
                    try:
                        # signing_cert is typically an asn1crypto.x509.Certificate
                        if signing_cert is not None and hasattr(signing_cert, "dump"):
                            thumb = hashlib.sha256(signing_cert.dump()).hexdigest()
                            subj = getattr(signing_cert, "subject", None)
                            if subj is not None and hasattr(subj, "native"):
                                name = subj.native.get("common_name")
                    except Exception:
                        pass

                    sigs.append(
                        {
                            "intact": intact,
                            "valid": valid,
                            "trusted": trusted,
                            "thumbprint": thumb,
                            "name": name,
                        }
                    )
                except Exception as e:
                    all_good = False
                    sigs.append({"error": str(e)})

        result["valid"] = bool(all_good)
        result["details"] = {"signatures": sigs}
        result["signer_cert_thumbprint"] = sigs[0].get("thumbprint") if sigs else None
        result["signer_name"] = sigs[0].get("name") if sigs else None

    except Exception as e:
        # If pyhanko fails unexpectedly, don't break the pipeline; fall back to heuristic.
        result["details"] = f"signature-like contents present but validation failed: {e}"

    return result
