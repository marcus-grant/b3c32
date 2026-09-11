# python/tests/test_codec.py
"""
Tests for the Crockford Base32 codec: known and periodic encode vectors,
cross-lineage encoder agreement, strict decode, roundtrip over the
exhaustive small domain, property laws, and lenient coercion.

Original of this file was moved from old main test module test_b3c32.py.
These original elements were from that module's state at 2026-07-22.

Author: Marcus Grant
OriginDate: 2026-07-22
Date: 2026-09-11
License: Apache-2.0
"""

import base64

import pytest
from hypothesis import given
from hypothesis import strategies as st

from b3c32 import (
    CROCKFORD32_ALPHABET,
    CoercionError,
    coerce_crockford_b32,
    decode_crockford_b32,
    encode_crockford_b32,
)
from tests.vectors import (
    KNOWN_ENCODE_VECTORS,
    PERIODIC_AA_VECTORS,
    PERIODIC_FF_VECTORS,
    PERIODIC_ZERO_VECTORS,
)

KNOWN_ENCODE_PYTEST = [pytest.param(x[0], x[1], id=x[2]) for x in KNOWN_ENCODE_VECTORS]
# Invert the KNOWN_ENCODE_VECTORS for decode tests: (encoded, original, id)
KNOWN_DECODE_PYTEST = [pytest.param(x[1], x[0], id=x[2]) for x in KNOWN_ENCODE_VECTORS]


def _exhaustive_small_inputs() -> list[bytes]:
    """Every byte string up to two bytes: empty, all 256 single bytes,
    all 65536 pairs. Small enough to enumerate, wide enough to cover
    the single-byte and cross-byte-boundary cases."""
    cases: list[bytes] = [b""]
    cases += [bytes([i]) for i in range(256)]
    cases += [bytes([i, j]) for i in range(256) for j in range(256)]
    return cases


class TestCrockfordEncode:
    """Contract 4.7 and 4.6. Fixed encoder vectors and periodic patterns.

    Known values are hand-derived and confirmed against independent
    codecs; the IETF draft rows are externally authored.
    """

    @pytest.mark.parametrize("data,expect", KNOWN_ENCODE_PYTEST)
    def test_known_encodings(self, data: bytes, expect: str):
        """Contract 4.7. Encoding matches hand-derived and draft values."""
        assert encode_crockford_b32(data) == expect

    def test_output_length(self):
        """Output length is ceil(input bits / 5). Local coverage."""
        assert len(encode_crockford_b32(b"\x00")) == 2  # 8 bits → 2 chars
        assert len(encode_crockford_b32(b"\x00" * 5)) == 8  # 40 bits → 8 chars
        assert len(encode_crockford_b32(b"\x00" * 15)) == 24  # 120 bits → 24 chars

    @pytest.mark.parametrize("length,expect", PERIODIC_AA_VECTORS)
    def test_periodic_aa(self, length: int, expect: str):
        """Contract 4.6. 0xAA at each pad residue. Alternating symbols
        catch ordering and transposition errors."""
        assert encode_crockford_b32(b"\xaa" * length) == expect

    @pytest.mark.parametrize("length,expect", PERIODIC_FF_VECTORS)
    def test_periodic_ff(self, length: int, expect: str):
        """Contract 4.6. 0xFF at each pad residue. Uniform period, so it
        confirms tail placement only and is blind to ordering."""
        assert encode_crockford_b32(b"\xff" * length) == expect

    @pytest.mark.parametrize("length,expect", PERIODIC_ZERO_VECTORS)
    def test_periodic_zero(self, length: int, expect: str):
        """Contract 4.6. 0x00 at each pad residue. Tail-blind; certifies
        length only, never pad behavior."""
        assert encode_crockford_b32(b"\x00" * length) == expect

    def test_long_tiling_matches_literal_encode(self):
        """Contract 4.6. A long 0xAA encode equals period-times-N plus
        tail. The expression is a cross-check and failure localizer, not
        the source of the expected value."""
        literal = encode_crockford_b32(b"\xaa" * 105)
        assert literal == "NA" * 84


class TestEncoderCrossLineage:
    """Contract 4.5. Shipped encoder agrees with an independent-lineage
    verifier.

    The shipped encoder is shift-and-mask bitstream; the verifier is
    stdlib RFC 4648 base32 with padding stripped and the alphabet
    translated to Crockford. They share no code, so agreement over
    arbitrary inputs certifies bit-mechanics (windowing, low-pad,
    length) beyond the fixed hand-derived vectors.
    """

    _RFC4648_B32 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"

    def _crock32_verifier(self, data: bytes) -> str:
        """Independent-lineage Crockford encoder for cross-checking.

        Uses stdlib base64.b32encode (RFC 4648), strips '=' padding, and
        translates the RFC 4648 alphabet to Crockford. Shares no code with
        encode_crockford_b32; used only in tests as the cross-lineage
        oracle.
        """
        _CROCK_TRANS = str.maketrans(self._RFC4648_B32, CROCKFORD32_ALPHABET)
        b32 = base64.b32encode(data).decode("ascii").rstrip("=")
        return b32.translate(_CROCK_TRANS)

    @pytest.mark.parametrize("data,expect", KNOWN_ENCODE_PYTEST)
    def test_matches_known_vectors(self, data, expect):
        """The verifier independently reproduces every known-value vector.

        Anchors the verifier before it is trusted as the cross-lineage
        oracle: if the stdlib-plus-translation verifier reproduces the
        externally-authored draft rows and the hand-derived cases, it is
        a trustworthy independent check on the shipped encoder. A failure
        here means the verifier itself is wrong, not the encoder.
        """
        _ = expect  # To shut up LSP
        assert encode_crockford_b32(data) == self._crock32_verifier(data)

    def test_agrees_exhaustive_small(self):
        """Shipped encoder and verifier agree on every input up to two
        bytes: proof over the small domain, not a sample.

        Covers all 256 single-byte and 65536 two-byte inputs plus the
        empty input. Longer lengths and the remaining pad residues are
        covered by the random test.
        """
        for data in _exhaustive_small_inputs():
            msg = f"mismatch on {data!r}"
            assert encode_crockford_b32(data) == self._crock32_verifier(data), msg

    @given(st.binary(max_size=256))
    def test_agrees_on_generated_inputs(self, data: bytes):
        """Shipped encoder and verifier agree on generated inputs."""
        assert encode_crockford_b32(data) == self._crock32_verifier(data)


class TestDecodeCrockfordB32:
    """Contract section 5, not a numbered assertion class. Strict decode
    is the inverse of the encoder.

    Symbols are taken MSB-first in 5-bit groups and trailing bits that
    do not complete a byte are discarded, since those bits are pad the
    encoder introduced to fill a symbol, not input. This makes decode
    recover the original bytes exactly, so the known vectors invert.
    Input must already be canonical; leniency is composed by passing
    through coerce_crockford_b32 first.
    """

    @pytest.mark.parametrize("code,expect", KNOWN_DECODE_PYTEST)
    def test_inverts_known_vectors(self, code, expect):
        """Every known encode vector decodes back to its original bytes."""
        assert decode_crockford_b32(code) == expect

    @pytest.mark.parametrize("bad", ["I", "L", "O", "U"])
    def test_rejects_ambiguous_letters(self, bad: str):
        """Visually ambiguous symbols rejected. Coerce to 0,1 with coerce_crockford_b32.
        So strict decode rejecting them is what keeps the layers distinct."""
        with pytest.raises(ValueError):
            decode_crockford_b32(f"ABC{bad}123")

    @pytest.mark.parametrize("bad", ["a", "b", "z"])
    def test_rejects_lowercase(self, bad: str):
        """Strict decode is case-sensitive; coerce first."""
        with pytest.raises(ValueError):
            decode_crockford_b32(f"ABC{bad}123")

    @pytest.mark.parametrize("bad", ["*", "~", "$", "=", "U"])
    def test_rejects_checksum_symbols(self, bad: str):
        """Mod-37 check symbols are reserved, not data.
        Strict decode doesnt checksum; rejects rather than treating them as payload."""
        with pytest.raises(ValueError):
            decode_crockford_b32(f"ABC{bad}123")

    @pytest.mark.parametrize("bad", ["!", "-", " ", ":", "_", "@", "\n"])
    def test_rejects_other_non_alphabet(self, bad: str):
        """Other symbols outside the alphabet raises.
        Separators & whitespace included because coerce_crockford_b32 strips them.
        Their rejection here confirms strict decode does no normalization."""
        with pytest.raises(ValueError):
            decode_crockford_b32(f"ABC{bad}123")


class TestCodecRoundtrip:
    """Contract 4.8, fixed and exhaustive cases. Encoding then decoding
    recovers the original bytes.

    This is a property of the encoder and decoder as a pair, not of
    either alone, which is why it lives in its own class. It holds in
    the bytes-first direction only: decode discards trailing bits that
    do not complete a byte, so a code whose bit length is not a byte
    multiple loses its final partial symbol and encode(decode(code)) is
    not a law. Asserting only the direction that holds keeps the
    asymmetry explicit rather than looking like a missing test.
    """

    def test_roundtrips_exhaustive_small(self):
        """Every input up to two bytes survives encode then decode."""
        for data in _exhaustive_small_inputs():
            msg = f"mismatch on {data!r}"
            assert decode_crockford_b32(encode_crockford_b32(data)) == data, msg

    @pytest.mark.parametrize("data,expect", KNOWN_ENCODE_PYTEST)
    def test_roundtrips_known_vectors(self, data: bytes, expect: str):
        """Every known vector's original bytes survive the round trip."""
        _ = expect  # To shut up LSP
        assert decode_crockford_b32(encode_crockford_b32(data)) == data


class TestCodecProperties:
    """Contract 4.8. Property laws over generated inputs.

    Hypothesis generates and shrinks, so a failure reports the minimal
    input rather than whatever random draw hit it.
    """

    @given(st.binary(max_size=256))
    def test_roundtrip(self, data: bytes):
        """decode(encode(x)) recovers x for any byte input."""
        assert decode_crockford_b32(encode_crockford_b32(data)) == data

    @given(st.binary(max_size=256))
    def test_alphabet_closure(self, data: bytes):
        """Encoded output contains only alphabet symbols."""
        assert set(encode_crockford_b32(data)) <= set(CROCKFORD32_ALPHABET)

    @given(st.binary(max_size=256))
    def test_length_invariant(self, data: bytes):
        """Output length is ceil(input bits / 5)."""
        assert len(encode_crockford_b32(data)) == -(-len(data) * 8 // 5)

    @given(st.binary(min_size=5, max_size=256), st.binary(max_size=256))
    def test_prefix_law(self, head: bytes, tail: bytes):
        """Encoding a 40-bit-aligned prefix prefixes the whole encoding."""
        aligned = head[: len(head) // 5 * 5]
        prefix = encode_crockford_b32(aligned)
        assert encode_crockford_b32(aligned + tail).startswith(prefix)


class TestCoerceCrockfordB32:
    """Contract section 5, the lenient side. Normalizes user-typed input
    toward canonical form.

    Coerces O to 0 and I and L to 1 unconditionally, since those are
    invalid in both the data alphabet and the checksum set. U is
    rejected, not coerced: it is the mod-37 check symbol, and coercing
    it to V waits on an explicit non-checksum declaration that no caller
    can yet make.
    """

    def test_uppercase_valid_input(self):
        """Valid lowercase input should be upper cased"""
        assert coerce_crockford_b32("abcd1234") == "ABCD1234"

    @pytest.mark.parametrize(
        "code,expect",
        [
            pytest.param("oil1", "0111", id="lowercase_ambiguous"),
            pytest.param("OIL1OIL", "0111011", id="uppercase_ambiguous"),
            pytest.param("oIl1OiL", "0111011", id="mixcase_ambiguous"),
        ],
    )
    def test_ambiguous_char_mappings(self, code: str, expect: str):
        """Ambiguous characters O, I, L should map to 0, 1, 1."""
        assert coerce_crockford_b32(code) == expect

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
        assert coerce_crockford_b32(code) == expect

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
        """Invalid characters should raise CoercionError."""
        with pytest.raises(CoercionError):
            coerce_crockford_b32(code)

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
        """Empty string after normalization should raise CoercionError."""
        with pytest.raises(CoercionError):
            coerce_crockford_b32(code)

    @pytest.mark.parametrize(
        "code",
        [
            pytest.param("abcd123", id="simple"),
            pytest.param("oil1", id="ambiguous"),
            pytest.param("ab-cd 12", id="separators"),
            pytest.param("  OIL-O  ", id="mixed"),
        ],
    )
    def test_idempotent(self, code: str):
        """Coercing twice should produce same result as once"""
        once = coerce_crockford_b32(code)
        twice = coerce_crockford_b32(once)
        assert once == twice
