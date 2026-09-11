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

from typing import Self

from blake3 import blake3

from b3c32.errors import UncertifiedWidthError

_CERTIFIED_BITS = frozenset({120})


class _IncrementalDigest:
    """Unkeyed blake3 fed in chunks, cut at a certified width.

    The hashing primitive; everything that produces a digest goes
    through it. hash_digest is the whole-input special case.

    Unkeyed is load-bearing: a key would make identical content produce
    different digests, defeating content addressing. No key or context
    string is ever accepted here.

    The digest depends only on the concatenation of the chunks fed, in
    any partitioning, empty chunks included. blake3 hashes 1024-byte
    leaves into a tree and compresses in 64-byte blocks; update
    boundaries have no relation to either and must not affect output.

    Width is enforced at the XOF cut, in digest, against the certified
    set; this is the single point of enforcement for the library.

    Certification: reference inputs from the pinned vector file are fed
    under partitionings that cross and sit on the leaf and block
    boundaries, and every one must reproduce the pinned hex at full
    extended-output width.
    """

    def __init__(self) -> None:
        self._hasher = blake3()

    def update(self, chunk: bytes) -> Self:
        """Feed one chunk; returns self so calls chain. Empty is a no-op."""
        self._hasher.update(chunk)
        return self

    def digest(self, bits: int) -> bytes:
        """Cut the XOF at bits; raises UncertifiedWidthError off the set.

        Non-consuming: may be called mid-feed and again after further
        updates, each call reflecting everything fed so far.
        """
        if bits not in _CERTIFIED_BITS:
            raise UncertifiedWidthError(bits)
        return self._hasher.digest(length=bits // 8)


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
