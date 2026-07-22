import hashlib

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
    result = ""
    for i in range(symbol_count):
        symbol_num = (num >> (5 * (symbol_count - 1 - i))) & 0b11111
        result += _CROCKFORD32[symbol_num]
    return result


def hash_full_b32(data: bytes) -> str:
    """Compute a BLAKE2b 120-bit hash and return as Crockford Base32 string.

    Args:
        data: The bytes to hash.

    Returns:
        A 24-character Crockford Base32 encoded string representing
        the 120-bit BLAKE2b hash digest.
    """
    digest = hashlib.blake2b(data, digest_size=15).digest()
    return _encode_crockford_b32(digest)


_TRANS_CROCKFORD_AMBIG = str.maketrans(
    {
        "O": "0",
        "I": "1",
        "L": "1",
        "U": "V",
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
