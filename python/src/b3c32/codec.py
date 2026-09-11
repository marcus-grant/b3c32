# python/src/b3c32/codec.py
"""
Crockford Base32 codec: low-pad bitstream encode, strict decode, and
lenient coercion of human input toward the canonical form.

Directly moved from old core.py module.
That was the home of everything shown by (OriginDate).

Author: Marcus Grant
OriginDate: 2026-07-24
Date: 2026-09-11
License: Apache-2.0
"""

from b3c32.errors import CoercionError

_TRANS_CROCKFORD_AMBIG = str.maketrans({"O": "0", "I": "1", "L": "1"})

CROCKFORD32_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


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
        symbols.append(CROCKFORD32_ALPHABET[symbol_num])
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
        symbol_int_value = CROCKFORD32_ALPHABET.index(symbol)
        # Shift left 5 to make room, OR to append this symbol's bits
        accumulated_int = (accumulated_int << 5) | symbol_int_value
    bit_count = 5 * len(code)
    # Trailing bits past the last whole byte are encoder pad, so drop them
    accumulated_int >>= bit_count % 8
    return accumulated_int.to_bytes(bit_count // 8, "big")


def coerce_crockford_b32(code: str) -> str:
    """Coerce user-supplied code for non-strict decodes/lookups.

    Args:
        code: User-supplied code string.

    Returns:
        Canonical uppercase string with ambiguous chars normalized.

    Raises:
        CoercionError: If code is empty or contains invalid characters.
    """
    s = code.strip().upper()
    s = s.replace("-", "").replace(" ", "")
    s = s.translate(_TRANS_CROCKFORD_AMBIG)

    if not s:
        raise CoercionError()

    for ch in s:
        if ch not in CROCKFORD32_ALPHABET:
            raise CoercionError(ch)
    return s
