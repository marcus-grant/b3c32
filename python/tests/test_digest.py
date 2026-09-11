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
from blake3 import blake3

from b3c32 import UncertifiedWidthError, hash_digest
from b3c32.digest import _CERTIFIED_BITS
from tests.vectors import _reference_input


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
