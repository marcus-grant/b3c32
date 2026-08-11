# python/src/b3c32/__init__.py
"""
b3c32: compact, hand-writable, prefix-matchable XOF hashes.
Author: Marcus Grant
Date: 2026-07-24
License: Apache-2.0
"""

from b3c32.core import (
    CROCKFORD32_ALPHABET,
    coerce_crockford_b32,
    decode_crockford_b32,
    encode_crockford_b32,
    hash_b32,
    hash_digest,
)
from b3c32.errors import CoercionError, UncertifiedWidthError
from b3c32.smoke import verify_conformance

__all__ = [
    "CROCKFORD32_ALPHABET",
    "CoercionError",
    "UncertifiedWidthError",
    "coerce_crockford_b32",
    "decode_crockford_b32",
    "encode_crockford_b32",
    "hash_b32",
    "hash_digest",
    "verify_conformance",
]
