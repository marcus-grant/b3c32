from blake3 import blake3

_HASH_DIGEST_LEN_BYTES = 15
_CROCKFORD32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _encode_crockford_b32(data: bytes) -> str:
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


def _hash_digest(data: bytes) -> bytes:
    """Compute the content digest for a shortcode.

    Unkeyed BLAKE3, sliced to 120 bits (15 bytes) on the 40-bit ladder.
    Unkeyed is load-bearing: keying would make identical content produce
    different addresses, defeating content-addressing.

    Args:
        data: The bytes to hash.

    Returns:
        The 15-byte digest.
    """
    return blake3(data).digest(length=_HASH_DIGEST_LEN_BYTES)


def _decode_crockford_b32(code: str) -> bytes:
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


_ = _decode_crockford_b32  # Shut up LSPs


def hash_full_b32(data: bytes) -> str:
    """Compute the canonical shortcode for content.
    Composes the certified units per the shared conformance contract:
    unkeyed BLAKE3 at 120 bits on the 40-bit ladder,
    encoded low-pad bitstream Crockford Base32.
    Both halves are contract-strict; this function only wires them.

    Args:
        data: The bytes to hash.

    Returns:
        A 24-character canonical Crockford Base32 shortcode.
    """
    return _encode_crockford_b32(_hash_digest(data))


_TRANS_CROCKFORD_AMBIG = str.maketrans(
    {
        "O": "0",
        "I": "1",
        "L": "1",
    }
)


def canonicalize_code(code: str) -> str:
    """Canonicalize user-supplied code for DB lookup.

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
