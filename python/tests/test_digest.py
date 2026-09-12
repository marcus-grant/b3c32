# python/tests/test_digest.py
"""
Tests for the digest layer: hard-shape reference vectors, full-width
extended-output equality, the runtime prefix property, and the
certified-width gate.

Original of this file was moved from old main test module test_b3c32.py.
These original elements were from that module's state at 2026-07-22.

Author: Marcus Grant
OriginDate: 2026-07-22
Date: 2026-09-11
License: Apache-2.0
"""

import hashlib
import json
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from b3c32 import UncertifiedWidthError, hash_digest
from b3c32.digest import CERTIFIED_BITS, _IncrementalDigest
from tests.vectors import chunked, reference_input

# Feed patterns are (chunk_size, interleave_empty). Sizes are chosen
# against blake3's structure, 1024-byte leaves and 64-byte blocks, not
# against the 40-bit codec ladder, which is the encoder's axis.
FEED_PATTERNS = [
    pytest.param(None, False, id="whole"),
    pytest.param(1023, False, id="leaf_minus_one"),
    pytest.param(1024, False, id="leaf_exact"),
    pytest.param(999, False, id="coprime_odd"),
    pytest.param(1, False, id="single_byte"),
    pytest.param(1023, True, id="leaf_minus_one_with_empties"),
]


def _feed(
    data: bytes, chunk_size: int | None, interleave_empty: bool
) -> _IncrementalDigest:
    """Feed data to a fresh primitive under the pattern; empties go
    before, between, and after every chunk when interleave_empty."""
    h = _IncrementalDigest()
    if interleave_empty:
        h.update(b"")
    for chunk in chunked(data, chunk_size):
        h.update(chunk)
        if interleave_empty:
            h.update(b"")
    return h


class TestIncrementalDigest:
    """Laws of the hashing primitive that need no external oracle.

    Certification with the pinned vector file is Test...DigestConformance's job;
    these are structural claims with ourselves as the oracle,
    guarded so a non-digest cannot pass."""

    def test_update_returns_self(self) -> None:
        """update chains: h.update(a).update(b) is h."""
        h = _IncrementalDigest()
        assert h.update(b"a") is h
        assert h.update(b"a").update(b"b") is h

    def test_empty_chunk_is_noop(self) -> None:
        """Empties before, between, and after chunks change nothing."""
        data = reference_input(2049)
        whole = _IncrementalDigest().update(data).digest(120)

        assert len(whole) == 15, "Returning None/empty is a silent failure"
        h = _IncrementalDigest().update(b"")
        for start in range(0, len(data), 1023):
            h.update(data[start : start + 1023]).update(b"")
        assert h.digest(120) == whole

    @given(st.binary(max_size=4096), st.integers(min_value=1, max_value=1100))
    def test_partitioning_invariance(self, data: bytes, chunk_size: int) -> None:
        """Metamorphic law: any partitioning equals the whole feed.

        Oracle is ourselves, so this is a law, not a certification.
        """
        whole = _IncrementalDigest().update(data).digest(120)
        assert len(whole) == 15

        h = _IncrementalDigest()
        for start in range(0, len(data), chunk_size):
            h.update(data[start : start + chunk_size])
        assert h.digest(120) == whole, f"chunk_size={chunk_size} len={len(data)}"


# BLAKE3's own published vector file, pinned and vendored.
# Each case is a dict with input_len and the reference hex fields;
# only "hash" is used.
VECTOR_FILE = Path(__file__).parents[2] / "vectors" / "blake3-1.8.5-93a431c.json"


def _load_blake3_cases() -> list[dict]:
    """Reference cases from the vendored pinned vector file."""
    return json.loads(VECTOR_FILE.read_text(encoding="utf-8"))["cases"]


class TestIncrementalDigestConformance:
    """Contract 4.1, 4.2, 4.3. The shipped hasher against reference
    vectors, proven under the feed matrix.

    Expected values come from the vendored reference file,
    never from the implementation's own hasher,
    so the assertion can detect a wrong hasher,
    rather than comparing it against itself.
    Inputs are reconstructed by the rule the reference file states:
    byte i is i mod 251.
    Only the unkeyed hash field is used;
    keyed_hash and derive_key are other modes and are not this scheme.

    The feed matrix adds an axis the contract does not yet name: where
    update boundaries fall against blake3's 1024-byte leaves and 64-byte
    blocks. Its documentation lands with the streaming surface."""

    def test_vector_file_matches_pinned_hash(self):
        """Contract 2.1. Vendored file matches the pinned SHA-256."""
        expect = "dcb91ea8accc77e6d6e632af7cdc1a99a9f3ae78cf648da595c7d064db32f624"
        actual = hashlib.sha256(VECTOR_FILE.read_bytes()).hexdigest()
        assert actual == expect

    @pytest.mark.parametrize("chunk_size,interleave_empty", FEED_PATTERNS)
    def test_digest_matches_reference_prefix(
        self, chunk_size: int | None, interleave_empty: bool
    ):
        """Contract 4.1. Digest == reference hex in every case, & every feed pattern."""
        for case in _load_blake3_cases():
            msg = f"mismatch on input_len={case['input_len']}"
            expect = bytes.fromhex(case["hash"][:30])
            data = reference_input(case["input_len"])
            assert _feed(data, chunk_size, interleave_empty).digest(120) == expect, msg

    @pytest.mark.parametrize("chunk_size,interleave_empty", FEED_PATTERNS)
    def test_digest_is_120_bits(self, chunk_size: int | None, interleave_empty: bool):
        """Digest width is 15 bytes. Local coverage, not a contract clause."""
        assert len(_feed(b"", chunk_size, interleave_empty).digest(120)) == 15
        assert len(_feed(b"x" * 1025, chunk_size, interleave_empty).digest(120)) == 15

    @pytest.mark.parametrize("chunk_size,interleave_empty", FEED_PATTERNS)
    def test_chunk_boundary_lengths(
        self, chunk_size: int | None, interleave_empty: bool
    ):
        """Contract 4.1. Chunk boundaries the reference singles out,
        reproduced under every feed pattern."""
        boundaries = {1023, 1024, 1025, 2048, 2049}
        cases = [c for c in _load_blake3_cases() if c["input_len"] in boundaries]
        assert len(cases) == len(boundaries)
        for case in cases:
            data = reference_input(case["input_len"])
            digest = _feed(data, chunk_size, interleave_empty).digest(120)
            msg = f"chunk boundary mismatch at input_len={case['input_len']}"
            assert digest == bytes.fromhex(case["hash"][:30]), msg

    @pytest.mark.parametrize("chunk_size,interleave_empty", FEED_PATTERNS)
    def test_reference_output_full_equality(
        self, chunk_size: int | None, interleave_empty: bool
    ) -> None:
        """Contract 4.2. Shipped hasher reproduces every byte of the
        reference extended output, crossing the 64-byte XOF block, from
        a chunk-fed state under every feed pattern.

        Reaches the private hasher: the certified-width gate in digest
        makes full width unreachable by design, and this is the one
        place the extended output must be checked past the gate.
        """
        for case in _load_blake3_cases():
            full = bytes.fromhex(case["hash"])
            assert len(full) > 64, "reference output must cross the XOF block"
            data = reference_input(case["input_len"])
            fed = _feed(data, chunk_size, interleave_empty)
            actual = fed._hasher.digest(length=len(full))
            msg = f"full output mismatch at input_len={case['input_len']}"
            assert actual == full, msg

    @pytest.mark.parametrize("chunk_size,interleave_empty", FEED_PATTERNS)
    def test_shipped_build_is_prefix_consistent(
        self, chunk_size: int | None, interleave_empty: bool
    ) -> None:
        """Contract 4.3. Shipped build's short output byte-prefixes its
        long output, compared region crossing the 64-byte XOF block,
        from a chunk-fed state; the certified cut prefixes it too."""
        for data in [b"", b"\x00", b"hello", b"x" * 1025]:
            fed = _feed(data, chunk_size, interleave_empty)
            long_output = fed._hasher.digest(length=131)
            short_output = fed._hasher.digest(length=70)
            certified = fed.digest(120)
            msg = f"shipped build prefix broken on {data!r}"
            assert long_output.startswith(short_output), msg
            assert long_output.startswith(certified), msg

    def test_digest_is_non_consuming(self) -> None:
        """A mid-feed digest call does not disturb the final digest.

        Pinned to the reference file: a destructive finalise or a
        state reset on digest would produce a plausible wrong value.
        """
        case = next(c for c in _load_blake3_cases() if c["input_len"] == 2049)
        expect = bytes.fromhex(case["hash"][:30])
        chunks = chunked(reference_input(2049), 1023)

        h = _IncrementalDigest().update(chunks[0])
        h.digest(120)
        for chunk in chunks[1:]:
            h.update(chunk)
        first = h.digest(120)
        assert first == expect
        assert h.digest(120) == first


class TestHashDigest:
    """hash_digest is the whole-input special case of the primitive.

    Certification lives in TestIncrementalDigestConformance; here only
    delegation is pinned: identity with the whole-fed primitive on a
    reference input, and the width gate reached through this name.
    """

    def test_is_whole_input_special_case(self) -> None:
        """Identity with the primitive fed whole, on a reference input."""
        data = reference_input(2049)
        assert hash_digest(data, 120) == _IncrementalDigest().update(data).digest(120)

    def test_uncertified_width_raises_through_delegation(self) -> None:
        """The gate is reached through the public name."""
        with pytest.raises(UncertifiedWidthError):
            hash_digest(b"", 64)


class TestCertifiedWidthGate:
    """The primitive gates on the certified width set at the XOF cut,
    the single point of enforcement; hash_digest reaches it by delegation.
    Consumer smoke tests depend on this gate surviving upgrades."""

    @pytest.mark.parametrize(
        "case",
        [0, 8, 42, 64, 119, 121, 128, 160, 256],
        ids=[
            "degenerate_len",
            "one_byte",
            "arbitrary",
            "off_ladder_64",
            "just_under",
            "just_over",
            "off_ladder_128",
            "on_ladder_uncertified",
            "off_ladder_256",
        ],
    )
    def test_uncertified_width_raises(self, case: int) -> None:
        """Any width outside the certified set raises UncertifiedWidthError."""
        with pytest.raises(UncertifiedWidthError):
            _IncrementalDigest().digest(case)

    def test_certified_set_is_exactly_120(self) -> None:
        """The certified set contains 120 and nothing else."""
        assert CERTIFIED_BITS == {120}
