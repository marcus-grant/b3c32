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

import os
from collections.abc import Iterable
from typing import BinaryIO

from b3c32.codec import encode_crockford_b32
from b3c32.digest import hash_digest
from b3c32.stream import (
    OptionalCallback,
    digest_from_chunks,
    digest_from_path,
    digest_from_stream,
)


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


def code_from_chunks(
    chunks: Iterable[bytes],
    bits: int,
    *,
    on_progress: OptionalCallback = None,
    interval_ms: int = 1000,
) -> str:
    """b3c32 code for an iterable of chunks: digest_from_chunks, encoded."""
    return encode_crockford_b32(
        digest_from_chunks(
            chunks, bits, on_progress=on_progress, interval_ms=interval_ms
        )
    )


def code_from_stream(
    stream: BinaryIO,
    bits: int,
    *,
    read_size: int = 1 << 20,
    on_progress: OptionalCallback = None,
    interval_ms: int = 1000,
) -> str:
    """b3c32 code for a binary stream: digest_from_stream, encoded."""
    return encode_crockford_b32(
        digest_from_stream(
            stream,
            bits,
            read_size=read_size,
            on_progress=on_progress,
            interval_ms=interval_ms,
        )
    )


def code_from_path(
    path: str | os.PathLike[str],
    bits: int,
    *,
    read_size: int = 1 << 20,
    on_progress: OptionalCallback = None,
    interval_ms: int = 1000,
) -> str:
    """b3c32 code for a file: digest_from_path, encoded."""
    return encode_crockford_b32(
        digest_from_path(
            path,
            bits,
            read_size=read_size,
            on_progress=on_progress,
            interval_ms=interval_ms,
        )
    )
