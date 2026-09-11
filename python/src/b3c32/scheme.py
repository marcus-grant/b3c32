# python/src/b3c32/scheme.py
"""
The b3c32 scheme: composition of the digest layer and the codec.

Reference input, certified digest, Crockford encoding, code.

Directly moved from old core.py module.
That was the home of everything shown by (OriginDate).

Author: Marcus Grant
OriginDate: 2026-07-24
Date: 2026-09-11
License: Apache-2.0
"""

from b3c32.codec import encode_crockford_b32
from b3c32.digest import hash_digest


def hash_b32(data: bytes, bits: int) -> str:
    """Compute the canonical code at a certified width.

    Composes hash_digest and the Crockford encoder.

    Args:
        data: The bytes to hash.
        bits: Digest width; must be in the certified set.

    Returns:
        Crockford Base32 code of bits // 5 characters.

    Raises:
        UncertifiedWidthError: bits is not a certified width.
    """
    return encode_crockford_b32(hash_digest(data, bits))
