# python/src/b3c32/__init__.py
"""
b3c32: compact, hand-writable, prefix-matchable XOF hashes.
Author: Marcus Grant
Date: 2026-07-24
License: Apache-2.0
"""

from b3c32.codec import (
    CROCKFORD32_ALPHABET,
    coerce_crockford_b32,
    decode_crockford_b32,
    encode_crockford_b32,
)
from b3c32.digest import CERTIFIED_BITS, hash_digest
from b3c32.errors import CoercionError, UncertifiedWidthError
from b3c32.scheme import code_from_chunks, code_from_path, code_from_stream, hash_b32
from b3c32.smoke import verify_conformance
from b3c32.stream import digest_from_chunks, digest_from_path, digest_from_stream

__all__ = [
    "CERTIFIED_BITS",
    "CROCKFORD32_ALPHABET",
    "CoercionError",
    "UncertifiedWidthError",
    "code_from_chunks",
    "code_from_path",
    "code_from_stream",
    "coerce_crockford_b32",
    "decode_crockford_b32",
    "digest_from_chunks",
    "digest_from_path",
    "digest_from_stream",
    "encode_crockford_b32",
    "hash_b32",
    "hash_digest",
    "verify_conformance",
]
