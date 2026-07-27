# python/src/b3c32/smoke.py
"""
Consumer smoke checks for contract drift detection.
Author: Marcus Grant
Date: 2026-07-27
License: Apache-2.0
"""

from b3c32 import (
    CoercionError,
    UncertifiedWidthError,
    coerce_crockford_b32,
    decode_crockford_b32,
    encode_crockford_b32,
    hash_b32,
)


def verify_conformance() -> None:
    """Assert the installed b3c32 still honors the contract surface.

    One curated assertion per contract claim a consumer depends on.
    Raises AssertionError naming the failed claim, or the library's
    own error types if raise behavior itself has drifted.

    Scope: drift detection through the public API only. Deep
    certification, including XOF output past the 64-byte block and
    exhaustive codec domains, is the library's own suite against the
    pinned reference file. A consumer build passing here is the
    certified surface at 120 bits; it is not itself a certification.
    """
    code = hash_b32(bytes(i % 251 for i in range(0)), 120)
    msg = f"smoke: pipeline vector mismatch at 120 bits, got {code}"
    assert code == "NW9MKEFNZ6GTD8209QN3DQ69", msg

    digest_wide = bytes(range(20))
    narrow = encode_crockford_b32(digest_wide[:15])
    wide = encode_crockford_b32(digest_wide)
    msg = "smoke: 40-bit prefix relation broken on aligned widths"
    assert wide.startswith(narrow), msg

    encoded = encode_crockford_b32(b"foobar")
    msg = f"smoke: non-aligned encode mismatch, got {encoded}"
    assert encoded == "CSQPYRK1E8", msg

    decoded = decode_crockford_b32("CSQPYRK1E8")
    assert decoded == b"foobar", f"smoke: decode inversion mismatch, got {decoded!r}"

    coerced = coerce_crockford_b32("oil-1")
    msg = f"smoke: coercion mismatch, got {coerced}"
    assert coerced == "0111", msg

    try:
        coerce_crockford_b32("!")
    except CoercionError:
        pass
    else:
        raise AssertionError("smoke: CoercionError not raised on invalid char")

    try:
        hash_b32(b"", 160)
    except UncertifiedWidthError:
        pass
    else:
        raise AssertionError("smoke: UncertifiedWidthError not raised at 160")
