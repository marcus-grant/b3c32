import pytest

from depo.util.shortcode import _encode_crockford_b32, canonicalize_code, hash_full_b32

# To indipendantly verify hashing and encoding...
# Use script in PROJECTROOT/scripts/hash-b32.sh
# To generate bit pattern strings to use with script:
# use scripts/generate-test-patterns.sh (NUM_BYTES) (PATTERN_NAME)
# Will print blake2b 120bit digest in hex and then Crockford base32
# As extra verification use https://cryptii.com/pipes/crockford-base32

CROCKFORD_STR = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
CROCKFORD_ALPHABET = set(CROCKFORD_STR)

# These are known blake2b 120bit hashes encoded in Crockford base32
# Empty bytes, made with b""
HASHB32_EMPTY = "PZDRE6BC90T0BS0FGG0ZM7Y9"
# "Hello, World!" string
HASHB32_HELLO = "D7GS0E632ZGYMQAVRXHYZ315"
# \xff (one all 1 byte)
HASHB32_1xFF_BYTES = "N07C0CD6R447SA6JT1CEVAWW"
# \x00 * 5 (five all 0 bytes)
HASHB32_5xZERO_BYTES = "DGGXXPQBAP0A56H3CJKG23P6"
# \x00 * 4099 (prime number len of \x00 bytes). 4099B is also more than a sector size
HASHB32_4099xZERO_BYTES = "DCJF8WQMWPFWGA3ZTB62HJA2"
# \xaa * 4099 (prime number len of \xaa bytes)
HASHB32_4099xAA_BYTES = "SXBV2Q0G5PZNCC60ED9AXGBZ"


class TestHashFullB32:
    """Tests the depo.util.shortcode.hash_full_b32 function"""

    @pytest.mark.parametrize(
        "data,expect",
        [
            (b"", HASHB32_EMPTY),
            (b"Hello, World!", HASHB32_HELLO),
            (b"\xff", HASHB32_1xFF_BYTES),
            (b"\x00" * 5, HASHB32_5xZERO_BYTES),
            (b"\x00" * 4099, HASHB32_4099xZERO_BYTES),
            (b"\xaa" * 4099, HASHB32_4099xAA_BYTES),
        ],
        ids=["empty", "Hello", "0xFF", "0x00 * 5", "0x00 * 4099", "0xAA * 4099"],
    )
    def test_known_b32_hashes(self, data: bytes, expect: str):
        """The hash/encode function must:
        1. Encode to the correct known value for given input
        2. Contain only Crockford base32 characters
        3. Length is always 24 characters (24 * 5 bits = 120 bits)
        4. Deterministic (same input always same output)
        5. Different inputs produce different outputs
        """
        result = hash_full_b32(data)
        assert result == expect  # (1)
        assert set(result).issubset(CROCKFORD_ALPHABET)  # (2)
        assert len(result) == 24  # (3)
        assert hash_full_b32(data) == result  # (4)
        assert hash_full_b32(data + b"x") != result  # (5)


class TestCrockfordEncode:
    """Tests for the _encode_crockford_b32 helper function.

    These values are hand-verifiable by converting to binary and grouping
    into 5-bit chunks, or via https://cryptii.com/pipes/crockford-base32
    """

    @pytest.mark.parametrize(
        "data,expect",
        [
            pytest.param(b"", "", id="empty"),
            pytest.param(b"\x00", "00", id="single_zero"),
            pytest.param(b"\x1f", "0Z", id="single_31"),
            pytest.param(b"\xff", "7Z", id="single_255"),
            pytest.param(b"\x00\x01", "0001", id="trailing_one"),
            pytest.param(b"\x84\x21", "1111", id="walking_ones"),
            pytest.param(b"\x00" * 5, "00000000", id="5x_zero"),
            pytest.param(b"\xff" * 5, "ZZZZZZZZ", id="5x_ff"),
        ],
    )
    def test_known_encodings(self, data: bytes, expect: str):
        """Verify encoding against hand-calculated values.

        Args:
            data: Input bytes to encode.
            expect: Expected Crockford Base32 output.
        """
        assert _encode_crockford_b32(data) == expect

    def test_output_length(self):
        """Output length should be ceil(input_bits / 5)."""
        assert len(_encode_crockford_b32(b"\x00")) == 2  # 8 bits → 2 chars
        assert len(_encode_crockford_b32(b"\x00" * 5)) == 8  # 40 bits → 8 chars
        assert len(_encode_crockford_b32(b"\x00" * 15)) == 24  # 120 bits → 24 chars

    def test_alphabet_compliance(self):
        """Output must only contain valid Crockford Base32 characters."""
        # Use bytes that would produce all possible 5-bit values (0-31)
        result = _encode_crockford_b32(bytes(range(256)))
        assert set(result).issubset(CROCKFORD_ALPHABET)
        # Verify excluded characters never appear
        assert not any(c in result for c in "ILOUilou")


class TestCanonicalizeCode:
    """Tests for the canonicalization of Crockford Base32 codes.

    This is not part of the original code but is important for real-world usage.
    """

    def test_uppercase_valid_input(self):
        """Valid lowercase input should be upper cased"""
        assert canonicalize_code("abcd1234") == "ABCD1234"

    @pytest.mark.parametrize(
        "code,expect",
        [
            pytest.param("oil1u", "0111V", id="lowercase_ambiguous"),
            pytest.param("OIL1OILU", "0111011V", id="uppercase_ambiguous"),
            pytest.param("oIl1OiLu", "0111011V", id="mixcase_ambiguous"),
        ],
    )
    def test_ambiguous_char_mappings(self, code: str, expect: str):
        """Ambiguous characters O, I, L should map to 0, 1, 1."""
        assert canonicalize_code(code) == expect

    @pytest.mark.parametrize(
        "code,expect",
        [
            pytest.param("ab-cd", "ABCD", id="hyphen"),
            pytest.param("ab cd", "ABCD", id="space"),
            pytest.param("ab-cd 12", "ABCD12", id="mixed_separators"),
            pytest.param("AB--CD", "ABCD", id="double_hyphen"),
        ],
    )
    def test_separators_removed(self, code: str, expect: str):
        """Hyphens and spaces should be stripped for readability."""
        assert canonicalize_code(code) == expect

    @pytest.mark.parametrize(
        "code",
        [
            pytest.param("FOO!", id="exclamation"),
            pytest.param("=", id="equals"),
            pytest.param("abc@def", id="at_sign"),
            pytest.param("test_123", id="underscore"),
        ],
    )
    def test_rejects_invalid_chars(self, code: str):
        """Invalid characters should raise ValueError."""
        with pytest.raises(ValueError):
            canonicalize_code(code)

    @pytest.mark.parametrize(
        "code",
        [
            pytest.param("", id="empty"),
            pytest.param(" ", id="space_only"),
            pytest.param("  ", id="multiple_spaces"),
            pytest.param("-", id="hyphen_only"),
            pytest.param("- -", id="hyphens_and_spaces"),
            pytest.param(" - - ", id="padded_separators"),
        ],
    )
    def test_rejects_empty_after_norm(self, code: str):
        """Empty string after normalization should raise ValueError."""
        with pytest.raises(ValueError):
            canonicalize_code(code)

    @pytest.mark.parametrize(
        "code",
        [
            pytest.param("abcd123", id="simple"),
            pytest.param("oil1", id="ambiguous"),
            pytest.param("ab-cd 12", id="separators"),
            pytest.param("  OIL-U  ", id="mixed"),
        ],
    )
    def test_idempotent(self, code: str):
        """Canonical twice should produce same result as once"""
        once = canonicalize_code(code)
        twice = canonicalize_code(once)
        assert once == twice
