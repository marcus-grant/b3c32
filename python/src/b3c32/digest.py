# python/src/b3c32/digest.py
"""
Digest layer: unkeyed blake3 XOF cut at a certified width.

Holds the certified-width set and the materialised-bytes digest.
The incremental digest lands here when streaming is implemented.

Directly moved from old core.py module.
That was the home of everything shown by (OriginDate).

Author: Marcus Grant
OriginDate: 2026-07-24
Date: 2026-09-11
License: Apache-2.0
"""

from blake3 import blake3

from b3c32.errors import UncertifiedWidthError

_CERTIFIED_BITS = frozenset({120})


def hash_digest(data: bytes, bits: int) -> bytes:
    """Compute the content digest at a certified width.

    Unkeyed BLAKE3 XOF sliced to bits, gated on the certified set.

    Args:
        data: The bytes to hash.
        bits: Digest width; must be in the certified set.

    Returns:
        The digest of bits // 8 bytes.

    Raises:
        UncertifiedWidthError: bits is not a certified width.
    """
    if bits not in _CERTIFIED_BITS:
        raise UncertifiedWidthError(bits)
    return blake3(data).digest(length=bits // 8)
