# python/tests/test_scheme.py
"""
Tests for the b3c32 scheme composition: wiring, frozen reference and
convenience codes, aligned prefixing, the alignment guard, and the
frozen file holding every hand-held literal.

Directly moved from old core.py module.
That was the home of everything shown by (OriginDate).

Author: Marcus Grant
OriginDate: 2026-07-24
Date: 2026-09-11
License: Apache-2.0
"""

import io
import json
from pathlib import Path

import pytest
from blake3 import blake3

from b3c32 import encode_crockford_b32, hash_b32, hash_digest
from b3c32.scheme import code_from_chunks, code_from_path, code_from_stream
from tests.vectors import (
    CONVENIENCE_ENCODED_VECTORS,
    KNOWN_ENCODE_VECTORS,
    REFERENCE_ENCODED_VECTORS,
    chunked,
    reference_input,
)

CONVENIENCE_ENCODED_PYTEST = [
    pytest.param(x[0], x[1], id=x[2]) for x in CONVENIENCE_ENCODED_VECTORS
]


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
        assert hash_b32(reference_input(input_len), 120) == expect

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


class TestCodeFromSources:
    """The streaming compositions: digest layer, then the codec.

    Composition itself is certified by TestHashB32 on the frozen codes;
    here each entry point gets one wiring test against hash_b32, plus
    one frozen-code check through the chunked route so the streaming
    composition is pinned to a published value, not only to ourselves.
    """

    def test_chunks_matches_hash_b32(self) -> None:
        """code_from_chunks over 1023-byte chunks equals hash_b32 whole."""
        data = reference_input(2049)
        assert code_from_chunks(chunked(data, 1023), 120) == hash_b32(data, 120)

    def test_stream_matches_hash_b32(self) -> None:
        """code_from_stream over io.BytesIO equals hash_b32 whole."""
        data = reference_input(2049)
        assert code_from_stream(io.BytesIO(data), 120) == hash_b32(data, 120)

    def test_path_matches_hash_b32(self, tmp_path: Path) -> None:
        """code_from_path over a file equals hash_b32 whole."""
        data = reference_input(2049)
        (path := tmp_path / "data.bin").write_bytes(data)
        assert code_from_path(path, 120) == hash_b32(data, 120)

    @pytest.mark.parametrize("input_len,expect", REFERENCE_ENCODED_VECTORS)
    def test_chunked_codes_match_frozen_set(self, input_len: int, expect: str):
        """Contract composition: every frozen reference code is reproduced
        through the chunked route with interleaved empties."""
        chunks = [b""]
        for chunk in chunked(reference_input(input_len), 1023):
            chunks += [chunk, b""]
        assert code_from_chunks(chunks, 120) == expect
