# python/src/b3c32/core.py
"""
BLAKE3 hashing and Crockford Base32 codec for b3c32 codes.
Author: Marcus Grant
Date: 2026-01-26
Revisions: [2026-07-24]
License: Apache-2.0
"""

from blake3 import blake3

from b3c32.errors import UncertifiedWidthError

_CROCKFORD32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
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


def encode_crockford_b32(data: bytes) -> str:
    """Encode bytes as Crockford Base32, low-pad bitstream.

    Bits are taken MSB-first as a single stream, grouped into 5-bit
    units from the left; a final partial group is zero-extended in the
    least-significant positions (low-pad) per the Base32-for-Humans
    draft, Section 3.1.

    Args:
        data: The bytes to encode.

    Returns:
        Crockford Base32 string, length ceil(len(data) * 8 / 5).
    """
    num, bit_count = int.from_bytes(data, byteorder="big"), len(data) * 8
    symbol_count = (bit_count + 4) // 5  # ceil(bits / 5)
    num <<= (5 - bit_count % 5) % 5  # low-pad to next 5-bit boundary
    symbols = []
    for i in range(symbol_count):
        symbol_num = (num >> (5 * (symbol_count - 1 - i))) & 0b11111
        symbols.append(_CROCKFORD32[symbol_num])
    return "".join(symbols)


def decode_crockford_b32(code: str) -> bytes:
    """Decode canonical Crockford Base32 to bytes.

    Symbols are taken MSB-first in 5-bit groups. Trailing bits that do
    not complete a byte are discarded: they are pad the encoder added to
    fill a whole symbol, never part of the input. Reference
    implementation of the encoding's inverse.

    Args:
        code: Canonical (uppercase, alphabet-only) Crockford string.

    Returns:
        The decoded bytes.

    Raises:
        ValueError: A character is outside the Crockford alphabet.
    """
    accumulated_int = 0
    for symbol in code:
        symbol_int_value = _CROCKFORD32.index(symbol)
        # Shift left 5 to make room, OR to append this symbol's bits
        accumulated_int = (accumulated_int << 5) | symbol_int_value
    bit_count = 5 * len(code)
    # Trailing bits past the last whole byte are encoder pad, so drop them
    accumulated_int >>= bit_count % 8
    return accumulated_int.to_bytes(bit_count // 8, "big")


_TRANS_CROCKFORD_AMBIG = str.maketrans(
    {
        "O": "0",
        "I": "1",
        "L": "1",
    }
)


def coerce_crockford_b32(code: str) -> str:
    """Coerce user-supplied code for non-strict decodes/lookups.

    Args:
        code: User-supplied code string.

    Returns:
        Canonical uppercase string with ambiguous chars normalized.

    Raises:
        ValueError: If code is empty or contains invalid characters.
    """
    s = code.strip().upper()
    s = s.replace("-", "").replace(" ", "")
    s = s.translate(_TRANS_CROCKFORD_AMBIG)

    if not s:
        raise ValueError("Code cannot be empty")

    for ch in s:
        if ch not in _CROCKFORD32:
            raise ValueError(f"Invalid character in code: {ch}")
    return s
