# python/tests/test_smoke.py
"""
Tests for the consumer smoke checks.
Author: Marcus Grant
Date: 2026-07-27
License: Apache-2.0
"""

import pytest

from b3c32 import encode_crockford_b32
from b3c32 import verify_conformance


class TestVerifyConformance:
    """The smoke entry point runs clean on a correct build."""

    def test_runs_clean(self) -> None:
        """A correct installation passes without raising."""
        verify_conformance()

    def test_red_on_vector_drift(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A drifted pipeline value fails with the claim named."""
        monkeypatch.setattr("b3c32.smoke.hash_b32", lambda data, bits: "WRONG")
        with pytest.raises(AssertionError, match="pipeline"):
            verify_conformance()

    def test_red_on_gate_loss(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A vanished width gate fails the raise check."""

        def fake_hash(data: bytes, bits: int) -> str:
            return "NW9MKEFNZ6GTD8209QN3DQ69"

        monkeypatch.setattr("b3c32.smoke.hash_b32", fake_hash)
        with pytest.raises(AssertionError, match="UncertifiedWidthError not raised"):
            verify_conformance()

    def test_red_on_inversion_drift(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A drifted decode fails the inversion claim in isolation."""

        def fake_decode(code: str) -> bytes:
            return b"WRONG"

        monkeypatch.setattr("b3c32.smoke.decode_crockford_b32", fake_decode)
        with pytest.raises(AssertionError, match="inversion"):
            verify_conformance()

    def test_red_on_prefix_drift(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A broken wide encoding fails the prefix claim in isolation."""
        real = encode_crockford_b32
        calls = {"n": 0}

        def fake_encode(data: bytes) -> str:
            calls["n"] += 1
            if calls["n"] == 2:
                return "WRONG" + real(data)[5:]
            return real(data)

        monkeypatch.setattr("b3c32.smoke.encode_crockford_b32", fake_encode)
        with pytest.raises(AssertionError, match="prefix"):
            verify_conformance()

    def test_red_on_encode_drift(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A drifted raw encode fails the non-aligned claim."""

        def fake_encode(data: bytes) -> str:
            return "WRONG"

        monkeypatch.setattr("b3c32.smoke.encode_crockford_b32", fake_encode)
        with pytest.raises(AssertionError, match="non-aligned|prefix"):
            verify_conformance()

    def test_red_on_coercion_drift(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A drifted coercion fails the coercion value claim."""

        def fake_coerce(code: str) -> str:
            return "WRONG"

        monkeypatch.setattr("b3c32.smoke.coerce_crockford_b32", fake_coerce)
        with pytest.raises(AssertionError, match="coercion"):
            verify_conformance()

    def test_red_on_coercion_gate_loss(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A coerce that stops raising fails the raise claim."""

        def fake_coerce(code: str) -> str:
            return "0111"

        monkeypatch.setattr("b3c32.smoke.coerce_crockford_b32", fake_coerce)
        with pytest.raises(AssertionError, match="CoercionError not raised"):
            verify_conformance()
