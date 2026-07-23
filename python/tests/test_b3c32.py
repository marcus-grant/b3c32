# tests/util/test_shortcode.py
"""
Tests for shortcode hashing and Crockford encoding.
Author: Marcus Grant
Date: 2026-01-26
Revisions: [2026-07-22]
License: Apache-2.0
"""

import base64
import hashlib
import json
import string
from pathlib import Path

import pytest
from blake3 import blake3
from hypothesis import given
from hypothesis import strategies as st

from depo.util.shortcode import (
    _CROCKFORD32,
    _HASH_DIGEST_LEN_BYTES,
    _decode_crockford_b32,
    _encode_crockford_b32,
    _hash_digest,
    canonicalize_code,
    hash_full_b32,
)

# Vectors here are hand-derived and confirmed against independent codecs.
# scripts/audit-conformance-vectors.sh rederives the published set using only
# external tools, with nothing from this implementation in the loop.

KNOWN_ENCODE_VECTORS = [
    (b"", "", "empty"),
    (b"\x00", "00", "single_zero"),  # Start hand-derived boundrary-crossing vectors
    (b"\x1f", "3W", "single_31"),
    (b"\xff", "ZW", "single_255"),
    (b"\x00\x01", "000G", "trailing_one"),
    (b"\x84\x21", "GGGG", "walking_ones"),
    (b"\x00" * 5, "00000000", "5x_zero"),
    (b"\xff" * 5, "ZZZZZZZZ", "5x_ff"),
    (b"\xaa\xaa\xaa", "NANAM", "3x_aa"),
    (b"f", "CR", "IETF-draft-f"),  # Start of draft IETF examples, Section 3.1
    (b"fo", "CSQG", "IETF-draft-fo"),
    (b"foo", "CSQPY", "IETF-draft-foo"),
    (b"foob", "CSQPYRG", "IETF-draft-foob"),
    (b"fooba", "CSQPYRK1", "IETF-draft-fooba"),
    (b"foobar", "CSQPYRK1E8", "IETF-draft-foobar"),
    (b"test", "EHJQ6X0", "IETF-draft-test"),
]

KNOWN_ENCODE_PYTEST = [pytest.param(x[0], x[1], id=x[2]) for x in KNOWN_ENCODE_VECTORS]
# Invert the KNOWN_ENCODE_VECTORS for decode tests: (encoded, original, id)
KNOWN_DECODE_PYTEST = [pytest.param(x[1], x[0], id=x[2]) for x in KNOWN_ENCODE_VECTORS]

# Contract 4.6. 0xAA repeated, lengths 10-14 covering all five pad residues.
PERIODIC_AA_VECTORS = [
    (10, "NANANANANANANANA"),
    (11, "NANANANANANANANAN8"),
    (12, "NANANANANANANANANAN0"),
    (13, "NANANANANANANANANANAM"),
    (14, "NANANANANANANANANANANAG"),
]

# Contract 4.6. 0xFF repeated, same lengths. Uniform period, tail-confirmer only.
PERIODIC_FF_VECTORS = [
    (10, "Z" * 16),
    (11, ("Z" * 17) + "W"),
    (12, ("Z" * 19) + "G"),
    (13, ("Z" * 20) + "Y"),
    (14, ("Z" * 22) + "R"),
]

# Contract 4.6. 0x00 repeated, same lengths. Tail-blind, certifies length only.
PERIODIC_ZERO_VECTORS = [
    (10, "0" * 16),
    (11, "0" * 18),
    (12, "0" * 20),
    (13, "0" * 21),
    (14, "0" * 23),
]

REFERENCE_ENCODED_VECTORS = [
    (0, "NW9MKEFNZ6GTD8209QN3DQ69"),
    (1023, "2088JW7EV8ZBJCNTNGA2HHX2"),
    (1024, "88GMEEFGJPJ0DWZWGFFBH2BM"),
    (1025, "T017HBJ7XCKV6KXESXKV9ZH6"),
    (2049, "BX6Q5X0DF9FR5CAWMASE8JRX"),
]

CONVENIENCE_ENCODED_VECTORS = [
    (b"Hello, World!\n", "C8SR6JYEF0BXP7J03F7EMAWB", "hello"),
    (b"\x00\xff\r\n\x1a", "56V71DGBAMEA57K94KP1NKF8", "hard_bytes"),
    (b"\xe2\x9c\x85", "2A9V46HDZYE86ESAZ71PZ8Y6", "check_emoji"),
]
CONVENIENCE_ENCODED_PYTEST = [
    pytest.param(x[0], x[1], id=x[2]) for x in CONVENIENCE_ENCODED_VECTORS
]


def _reference_input(input_len: int) -> bytes:
    """Reconstruct a reference input: byte i is i mod 251, per vector file rule."""
    return bytes(i % 251 for i in range(input_len))


def _exhaustive_small_inputs() -> list[bytes]:
    """Every byte string up to two bytes: empty, all 256 single bytes,
    all 65536 pairs. Small enough to enumerate, wide enough to cover
    the single-byte and cross-byte-boundary cases."""
    cases: list[bytes] = [b""]
    cases += [bytes([i]) for i in range(256)]
    cases += [bytes([i, j]) for i in range(256) for j in range(256)]
    return cases


class TestHashDigest:
    """The shipped hasher conforms to the BLAKE3 reference vectors.

    Expected values come from the vendored reference file, never from
    depo's own hasher, so the assertion can detect a wrong hasher rather
    than comparing it against itself. Inputs are reconstructed by the
    rule the reference file states: byte i is i mod 251. Only the
    unkeyed hash field is used; keyed_hash and derive_key are other
    modes and are not depo's scheme.
    """

    VECTOR_FILE = Path(__file__).parent.parent / "vectors" / "blake3-1.8.5-93a431c.json"

    def _load_blake3_cases(self) -> list[dict]:
        """Reference cases from the vendored pinned vector file."""
        return json.loads(self.VECTOR_FILE.read_text(encoding="utf-8"))["cases"]

    def test_vector_file_matches_pinned_hash(self):
        """Vendored reference file is byte-identical to the pinned SHA-256,
        so a swapped or corrupted file fails loud."""
        expect = "dcb91ea8accc77e6d6e632af7cdc1a99a9f3ae78cf648da595c7d064db32f624"
        actual = hashlib.sha256(self.VECTOR_FILE.read_bytes()).hexdigest()
        assert actual == expect

    def test_digest_matches_reference_prefix(self):
        """Digest == first 15 bytes of the reference hash for every case in the file."""
        for case in self._load_blake3_cases():
            msg = f"mismatch on input_len={case['input_len']}"
            expect = bytes.fromhex(case["hash"][:30])
            assert _hash_digest(_reference_input(case["input_len"])) == expect, msg

    def test_digest_is_120_bits(self):
        """The digest is exactly 15 bytes, the 120-bit current hash digest size."""
        assert _HASH_DIGEST_LEN_BYTES * 8 == 120
        assert len(_hash_digest(b"")) == _HASH_DIGEST_LEN_BYTES
        assert len(_hash_digest(b"x" * 1025)) == _HASH_DIGEST_LEN_BYTES

    def test_chunk_boundary_lengths(self):
        """Inputs at blake3's chunk boundaries conform: 1023, 1024, 1025,
        2048, 2049. Singled out because the reference documents them as
        where the chunk tree engages."""
        boundaries = {1023, 1024, 1025, 2048, 2049}
        cases = [c for c in self._load_blake3_cases() if c["input_len"] in boundaries]
        assert len(cases) == len(boundaries)
        for case in cases:
            digest = _hash_digest(_reference_input(case["input_len"]))
            msg = f"chunk boundary mismatch at input_len={case['input_len']}"
            assert digest == bytes.fromhex(case["hash"][:30]), msg

    def test_reference_output_is_prefix_consistent(self):
        """Contract 4.2. Digest prefixes reference output past the 64B XOF block."""
        for case in self._load_blake3_cases():
            data = _reference_input(case["input_len"])
            full = bytes.fromhex(case["hash"])
            msg = f"prefix broken at input_len={case['input_len']}"
            assert len(full) > 64, "reference output must cross the XOF block"
            assert full.startswith(_hash_digest(data)), msg

    def test_shipped_build_is_prefix_consistent(self):
        """Contract 4.3. Shipped blake3 short output prefixes a longer one."""
        for data in [b"", b"\x00", b"hello", b"x" * 1025]:
            long_output = blake3(data).digest(length=131)
            msg = f"shipped build prefix broken on {data!r}"
            assert len(long_output) > 64, "long output must cross the XOF block"
            assert long_output.startswith(_hash_digest(data)), msg


class TestCrockfordAlphabet:
    """The alphabet is pinned two independent ways, neither restating
    the module's literal.

    The first route rebuilds the alphabet from stdlib constants and the
    I, L, O, U exclusion rule, asserting the literal matches. The second
    pins it from spec facts alone: the digits block, the A and Z
    endpoints, the four skip transitions, and strict ascent. The routes
    share no source, so a typo in the literal fails the first and a
    wrong exclusion rule fails the second.
    """

    def test_matches_rule_construction(self):
        """The literal equals digits followed by uppercase letters with
        I, L, O, U removed, built from stdlib constants."""
        alphanum = string.digits + string.ascii_uppercase
        assert _CROCKFORD32 == "".join(c for c in alphanum if c not in "ILOU")

    def test_length_is_32(self):
        """The alphabet is exactly 32 symbols, one per 5-bit value."""
        assert len(_CROCKFORD32) == 32

    def test_symbols_unique(self):
        """No symbol repeats, every 5bit value maps to a distinct character."""
        assert len(set(_CROCKFORD32)) == 32

    def test_excludes_ambiguous_letters(self):
        """No I,L,O,U appear: 1st 3 ambiguous visually to 1,0; U reserved to checksum"""
        assert not any(c in _CROCKFORD32 for c in "ILOU")

    def test_digits_block(self):
        """First 10 symbols are digits 0 to 9 without stdlib string helpers."""
        assert _CROCKFORD32[:10] == "".join(str(n) for n in range(10))

    def test_letters_start_after_digits(self):
        """A appears at 10, after digits block, and Z at end index of 31."""
        assert _CROCKFORD32[10] == "A"
        assert _CROCKFORD32[31] == "Z"

    def test_skip_transitions_positional(self):
        """Skips at HJ, KM, NP, TV, pinning which are omitted in alphanum sequence."""
        assert _CROCKFORD32.index("H") + 1 == _CROCKFORD32.index("J")
        assert _CROCKFORD32.index("K") + 1 == _CROCKFORD32.index("M")
        assert _CROCKFORD32.index("N") + 1 == _CROCKFORD32.index("P")
        assert _CROCKFORD32.index("T") + 1 == _CROCKFORD32.index("V")

    def test_ordering_monotonic(self):
        """Digits 0-9 occupy indices 0-9 and letters ascend thereafter,
        so lexical order of encoded strings matches bit order."""
        previous_symbol = _CROCKFORD32[10]
        for current_symbol in _CROCKFORD32[11:]:
            msg = f"Alphabet order not monotonic: {previous_symbol} >= {current_symbol}"
            assert current_symbol > previous_symbol, msg
            previous_symbol = current_symbol


class TestCrockfordEncode:
    """Tests for the _encode_crockford_b32 helper function.

    These values are hand-verifiable by converting to binary and grouping
    into 5-bit chunks, many taken from Crockford's IETF draft examples.
    Found at https://datatracker.ietf.org/doc/html/draft-crockford-base32-03#section-3.1
    """

    @pytest.mark.parametrize("data,expect", KNOWN_ENCODE_PYTEST)
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

    @pytest.mark.parametrize("length,expect", PERIODIC_AA_VECTORS)
    def test_periodic_aa(self, length: int, expect: str):
        """Contract 4.6. 0xAA at each pad residue. Alternating symbols
        catch ordering and transposition errors."""
        assert _encode_crockford_b32(b"\xaa" * length) == expect

    @pytest.mark.parametrize("length,expect", PERIODIC_FF_VECTORS)
    def test_periodic_ff(self, length: int, expect: str):
        """Contract 4.6. 0xFF at each pad residue. Uniform period, so it
        confirms tail placement only and is blind to ordering."""
        assert _encode_crockford_b32(b"\xff" * length) == expect

    @pytest.mark.parametrize("length,expect", PERIODIC_ZERO_VECTORS)
    def test_periodic_zero(self, length: int, expect: str):
        """Contract 4.6. 0x00 at each pad residue. Tail-blind; certifies
        length only, never pad behavior."""
        assert _encode_crockford_b32(b"\x00" * length) == expect

    def test_long_tiling_matches_literal_encode(self):
        """Contract 4.6. A long 0xAA encode equals period-times-N plus
        tail. The expression is a cross-check and failure localizer, not
        the source of the expected value."""
        literal = _encode_crockford_b32(b"\xaa" * 105)
        assert literal == "NA" * 84


class TestEncoderCrossLineage:
    """Shipped encoder agrees with an independent-lineage verifier.

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
        _encode_crockford_b32; used only in tests as the cross-lineage
        oracle.
        """
        _CROCK_TRANS = str.maketrans(self._RFC4648_B32, _CROCKFORD32)
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
        assert _encode_crockford_b32(data) == self._crock32_verifier(data)

    def test_agrees_exhaustive_small(self):
        """Shipped encoder and verifier agree on every input up to two
        bytes: proof over the small domain, not a sample.

        Covers all 256 single-byte and 65536 two-byte inputs plus the
        empty input. Longer lengths and the remaining pad residues are
        covered by the random test.
        """
        for data in _exhaustive_small_inputs():
            msg = f"mismatch on {data!r}"
            assert _encode_crockford_b32(data) == self._crock32_verifier(data), msg

    @given(st.binary(max_size=256))
    def test_agrees_on_generated_inputs(self, data: bytes):
        """Shipped encoder and verifier agree on generated inputs."""
        assert _encode_crockford_b32(data) == self._crock32_verifier(data)


class TestDecodeCrockfordB32:
    """Strict decode is the inverse of the encoder.

    Symbols are taken MSB-first in 5-bit groups and trailing bits that
    do not complete a byte are discarded, since those bits are pad the
    encoder introduced to fill a symbol, not input. This makes decode
    recover the original bytes exactly, so the known vectors invert.
    Input must already be canonical; leniency is composed by passing
    through canonicalize_code first.
    """

    @pytest.mark.parametrize("code,expect", KNOWN_DECODE_PYTEST)
    def test_inverts_known_vectors(self, code, expect):
        """Every known encode vector decodes back to its original bytes."""
        assert _decode_crockford_b32(code) == expect

    @pytest.mark.parametrize("bad", ["I", "L", "O", "U"])
    def test_rejects_ambiguous_letters(self, bad: str):
        """Visually ambiguous symbols rejected. Coerce to 0,1 with canonicalize_code.
        So strict decode rejecting them is what keeps the layers distinct."""
        with pytest.raises(ValueError):
            _decode_crockford_b32(f"ABC{bad}123")

    @pytest.mark.parametrize("bad", ["a", "b", "z"])
    def test_rejects_lowercase(self, bad: str):
        """Strict decode is case-sensitive; canonicalize first."""
        with pytest.raises(ValueError):
            _decode_crockford_b32(f"ABC{bad}123")

    @pytest.mark.parametrize("bad", ["*", "~", "$", "=", "U"])
    def test_rejects_checksum_symbols(self, bad: str):
        """Mod-37 check symbols are reserved, not data.
        Strict decode doesnt checksum; rejects rather than treating them as payload."""
        with pytest.raises(ValueError):
            _decode_crockford_b32(f"ABC{bad}123")

    @pytest.mark.parametrize("bad", ["!", "-", " ", ":", "_", "@", "\n"])
    def test_rejects_other_non_alphabet(self, bad: str):
        """Other symbols outside the alphabet raises.
        Separators & whitespaceincluded because canonicalize_code strips them.
        Their rejection here confirms strict decode does no normalization."""
        with pytest.raises(ValueError):
            _decode_crockford_b32(f"ABC{bad}123")


class TestCodecRoundtrip:
    """Encoding then decoding recovers the original bytes.

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
            assert _decode_crockford_b32(_encode_crockford_b32(data)) == data, msg

    @pytest.mark.parametrize("data,expect", KNOWN_ENCODE_PYTEST)
    def test_roundtrips_known_vectors(self, data: bytes, expect: str):
        """Every known vector's original bytes survive the round trip."""
        _ = expect  # To shut up LSP
        assert _decode_crockford_b32(_encode_crockford_b32(data)) == data


class TestHashFullB32:
    """Contract 4.9, 4.10, 4.11. The composed shortcode function.
    Units are certified separately; composition proves wiring,
    the ladder prefix relation, and the guard against off-ladder widths.
    Frozen addresses are depo-derived and provisional until normpic convergence.
    """

    @pytest.mark.parametrize("data", [b"", b"x" * 1025, b"Hello, World!\n"])
    def test_wiring(self, data):
        """Contract 4.9. hash_full_b32 composes _hash_digest and the encoder."""
        assert hash_full_b32(data) == _encode_crockford_b32(_hash_digest(data))

    @pytest.mark.parametrize("input_len,expect", REFERENCE_ENCODED_VECTORS)
    def test_encoded_matches_frozen_set(self, input_len: int, expect: str):
        """Contract 4.9. Reference-input encodings match the frozen set.
        Certified: each derives from the pinned reference hex through certified encoder,
        so it detects error, not just change.
        """
        assert hash_full_b32(_reference_input(input_len)) == expect

    @pytest.mark.parametrize("data,expect", CONVENIENCE_ENCODED_PYTEST)
    def test_convenience_encodings_match_frozen_set(self, data: bytes, expect: str):
        """Convenience vectors, depo-derived. Documents byte-oriented input;
        detects change only, not error."""
        assert hash_full_b32(data) == expect

    @pytest.mark.parametrize("data", [b"", b"x" * 1025, b"Hello, World!\n"])
    def test_prefix_holds_across_aligned_widths(self, data: bytes):
        """Contract 4.10. Encoding prefixes a wider 40-bit-aligned encoding."""
        narrow = _encode_crockford_b32(blake3(data).digest(length=15))
        wide = _encode_crockford_b32(blake3(data).digest(length=20))
        assert wide.startswith(narrow), f"prefix broken on {data!r}"

    def test_prefix_requires_aligned_width(self):
        """Contract 4.11. Prefix holds when the narrow width is a 40-bit
        multiple, breaks when it is not."""
        data = b"\xff" * 20
        wide = _encode_crockford_b32(data)
        assert wide.startswith(_encode_crockford_b32(data[:15]))
        assert not wide.startswith(_encode_crockford_b32(data[:16]))


class TestCodecProperties:
    """Contract 4.8. Property laws over generated inputs.

    Hypothesis generates and shrinks, so a failure reports the minimal
    input rather than whatever random draw hit it.
    """

    @given(st.binary(max_size=256))
    def test_roundtrip(self, data: bytes):
        """decode(encode(x)) recovers x for any byte input."""
        assert _decode_crockford_b32(_encode_crockford_b32(data)) == data

    @given(st.binary(max_size=256))
    def test_alphabet_closure(self, data: bytes):
        """Encoded output contains only alphabet symbols."""
        assert set(_encode_crockford_b32(data)) <= set(_CROCKFORD32)

    @given(st.binary(max_size=256))
    def test_length_invariant(self, data: bytes):
        """Output length is ceil(input bits / 5)."""
        assert len(_encode_crockford_b32(data)) == -(-len(data) * 8 // 5)

    @given(st.binary(min_size=5, max_size=256), st.binary(max_size=256))
    def test_prefix_law(self, head: bytes, tail: bytes):
        """Encoding a 40-bit-aligned prefix prefixes the whole encoding."""
        aligned = head[: len(head) // 5 * 5]
        prefix = _encode_crockford_b32(aligned)
        assert _encode_crockford_b32(aligned + tail).startswith(prefix)


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
            pytest.param("oil1", "0111", id="lowercase_ambiguous"),
            pytest.param("OIL1OIL", "0111011", id="uppercase_ambiguous"),
            pytest.param("oIl1OiL", "0111011", id="mixcase_ambiguous"),
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
            pytest.param("  OIL-O  ", id="mixed"),
        ],
    )
    def test_idempotent(self, code: str):
        """Canonical twice should produce same result as once"""
        once = canonicalize_code(code)
        twice = canonicalize_code(once)
        assert once == twice
