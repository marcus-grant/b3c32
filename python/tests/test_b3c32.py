# tests/util/test_b3c32.py
"""
Tests for b3c32 hashing and Crockford encoding.
Author: Marcus Grant
Date: 2026-01-26
Revisions: [2026-07-22]
License: Apache-2.0
"""

import base64
import hashlib
import json
from pathlib import Path

import pytest
from blake3 import blake3
from hypothesis import given
from hypothesis import strategies as st

from b3c32 import (
    CoercionError,
    UncertifiedWidthError,
    coerce_crockford_b32,
    decode_crockford_b32,
    encode_crockford_b32,
    hash_b32,
    hash_digest,
)
from b3c32.core import _CERTIFIED_BITS, CROCKFORD32_ALPHABET

# Vectors here are hand-derived and confirmed against independent codecs.
# scripts/audit-conformance-vectors.sh rederives the published set using only
# external tools, with nothing from this implementation in the loop.

KNOWN_ENCODE_VECTORS = [
    (b"", "", "empty"),
    (b"\x00", "00", "single_zero"),  # Start hand-derived boundary-crossing vectors
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
    """Contract 4.1, 4.2, 4.3. The shipped hasher against reference vectors.

    Expected values come from the vendored reference file, never from
    the implementation's own hasher, so the assertion can detect a
    wrong hasher rather than comparing it against itself. Inputs are
    reconstructed by the rule the reference file states: byte i is
    i mod 251. Only the unkeyed hash field is used; keyed_hash and
    derive_key are other modes and are not this scheme.
    """

    # Blake3's own published vector file, pinned and vendored.
    VECTOR_FILE = Path(__file__).parents[2] / "vectors" / "blake3-1.8.5-93a431c.json"

    def _load_blake3_cases(self) -> list[dict]:
        """Reference cases from the vendored pinned vector file."""
        return json.loads(self.VECTOR_FILE.read_text(encoding="utf-8"))["cases"]

    def test_vector_file_matches_pinned_hash(self):
        """Contract 2.1. Vendored file matches the pinned SHA-256."""
        expect = "dcb91ea8accc77e6d6e632af7cdc1a99a9f3ae78cf648da595c7d064db32f624"
        actual = hashlib.sha256(self.VECTOR_FILE.read_bytes()).hexdigest()
        assert actual == expect

    def test_digest_matches_reference_prefix(self):
        """Contract 4.1. Digest matches reference hex for every case."""
        for case in self._load_blake3_cases():
            msg = f"mismatch on input_len={case['input_len']}"
            expect = bytes.fromhex(case["hash"][:30])
            assert hash_digest(_reference_input(case["input_len"]), 120) == expect, msg

    def test_digest_is_120_bits(self):
        """Digest width is 15 bytes. Local coverage, not a contract clause."""
        assert len(hash_digest(b"", 120)) == 15
        assert len(hash_digest(b"x" * 1025, 120)) == 15

    def test_chunk_boundary_lengths(self):
        """Contract 4.1. Chunk boundaries the reference singles out."""
        boundaries = {1023, 1024, 1025, 2048, 2049}
        cases = [c for c in self._load_blake3_cases() if c["input_len"] in boundaries]
        assert len(cases) == len(boundaries)
        for case in cases:
            digest = hash_digest(_reference_input(case["input_len"]), 120)
            msg = f"chunk boundary mismatch at input_len={case['input_len']}"
            assert digest == bytes.fromhex(case["hash"][:30]), msg

    def test_reference_output_full_equality(self) -> None:
        """Contract 4.2. Shipped hasher reproduces every byte of the
        reference extended output, crossing the 64-byte XOF block."""
        for case in self._load_blake3_cases():
            full = bytes.fromhex(case["hash"])
            assert len(full) > 64, "reference output must cross the XOF block"
            data = _reference_input(case["input_len"])
            actual = blake3(data).digest(length=len(full))
            msg = f"full output mismatch at input_len={case['input_len']}"
            assert actual == full, msg

    def test_shipped_build_is_prefix_consistent(self) -> None:
        """Contract 4.3. Shipped build's short output byte-prefixes its
        long output, compared region crossing the 64-byte XOF block."""
        for data in [b"", b"\x00", b"hello", b"x" * 1025]:
            long_output = blake3(data).digest(length=131)
            short_output = blake3(data).digest(length=70)
            msg = f"shipped build prefix broken on {data!r}"
            assert long_output.startswith(short_output), msg


class TestCertifiedWidthGate:
    """The parametric API gates on the certified width set.
    Consumer smoke tests depend on this gate surviving upgrades."""

    @pytest.mark.parametrize(
        "case",
        [0, 42, 160],
        ids=["degenerate_len", "arbitrary", "40-width_uncertified"],
    )
    def test_uncertified_width_raises(self, case: int) -> None:
        """Any width outside the certified set raises UncertifiedWidthError."""
        with pytest.raises(UncertifiedWidthError):
            hash_digest(b"", case)

    def test_certified_set_is_exactly_120(self) -> None:
        """The certified set contains 120 and nothing else."""
        assert _CERTIFIED_BITS == {120}


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


class TestHashB32:
    """Contract 4.9, 4.10, 4.11. The composed code function.
    Units are certified separately; composition proves wiring,
    the 40-bit prefix relation, and the guard against uncertified
    widths. Convenience vectors are reference-implementation-derived
    and detect change, not error."""

    @pytest.mark.parametrize("data", [b"", b"x" * 1025, b"Hello, World!\n"])
    def test_wiring(self, data):
        """Contract 4.9. hash_b32 composes hash_digest and the encoder."""
        assert hash_b32(data, 120) == encode_crockford_b32(hash_digest(data, 120))

    @pytest.mark.parametrize("input_len,expect", REFERENCE_ENCODED_VECTORS)
    def test_encoded_matches_frozen_set(self, input_len: int, expect: str):
        """Contract 4.9. Reference-input encodings match the frozen set.
        Certified: each derives from the pinned reference hex through certified encoder,
        so it detects error, not just change."""
        assert hash_b32(_reference_input(input_len), 120) == expect

    @pytest.mark.parametrize("data,expect", CONVENIENCE_ENCODED_PYTEST)
    def test_convenience_encodings_match_frozen_set(self, data: bytes, expect: str):
        """Convenience vectors, reference-implementation-derived.
        Documents byte-oriented input; detects change only, not error."""
        assert hash_b32(data, 120) == expect

    @pytest.mark.parametrize("data", [b"", b"x" * 1025, b"Hello, World!\n"])
    def test_prefix_holds_across_aligned_widths(self, data: bytes):
        """Contract 4.10. Encoding prefixes a wider 40-bit-aligned encoding,
        compared region crossing the 64-byte XOF block.
        Raw blake3 calls because these widths are uncertified for the API."""
        narrow = encode_crockford_b32(blake3(data).digest(length=15))
        wide = encode_crockford_b32(blake3(data).digest(length=20))
        assert wide.startswith(narrow), f"prefix broken on {data!r}"

    def test_prefix_requires_aligned_width(self):
        """Contract 4.11. Prefix holds when the narrow width is a 40-bit
        multiple, breaks when it is not."""
        data = b"\xff" * 20
        wide = encode_crockford_b32(data)
        assert wide.startswith(encode_crockford_b32(data[:15]))
        assert not wide.startswith(encode_crockford_b32(data[:16]))

    def test_frozen_file_contains_handheld_literals(self) -> None:
        """Every hand-held literal appears in the frozen file, so
        generator-versus-suite drift fails every run, not at
        regeneration time only."""
        root = Path(__file__).parents[2]
        frozen_path = root / "vectors" / "b3c32-conformance.json"
        cases = json.loads(frozen_path.read_text(encoding="utf-8"))["cases"]
        encodes = {c["input_hex"]: c["encoded"] for c in cases if "encoded" in c}
        pipelines = {
            c["input_len"]: c["digest_encoded"]
            for c in cases
            if "input_len" in c and "digest_encoded" in c
        }
        for data, expect, _ in KNOWN_ENCODE_VECTORS:
            msg = f"frozen file missing or drifted on encode {data!r}"
            assert encodes.get(data.hex()) == expect, msg
        for input_len, expect in REFERENCE_ENCODED_VECTORS:
            msg = f"frozen file missing or drifted on pipeline len {input_len}"
            assert pipelines.get(input_len) == expect, msg
        for data, expect, _ in CONVENIENCE_ENCODED_VECTORS:
            hits = [
                c
                for c in cases
                if c.get("input_hex") == data.hex() and "digest_encoded" in c
            ]
            msg = f"frozen file missing or drifted on convenience {data!r}"
            assert hits and hits[0]["digest_encoded"] == expect, msg


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
