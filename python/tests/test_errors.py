# python/tests/test_errors.py
"""
Tests for b3c32 exception types.
Author: Marcus Grant
Date: 2026-07-24
License: Apache-2.0
"""

from b3c32 import CoercionError, UncertifiedWidthError


class TestUncertifiedWidthError:
    """Width gate error type. Consumer smoke tests depend on this
    type surviving upgrades."""

    def test_is_value_error(self) -> None:
        """The error subclasses ValueError and names the offending width."""
        assert issubclass(UncertifiedWidthError, ValueError)

    def test_stores_bits(self) -> None:
        """The offending width is stored as the bits attribute."""
        assert UncertifiedWidthError(42).bits == 42

    def test_message_names_width(self) -> None:
        """The error message names the offending width."""
        expect = ["42", "certif", "digest"]
        assert all((s in str(UncertifiedWidthError(42)) for s in expect))


class TestCoercionError:
    """Coercion failure type. Consumer catch surface for coerce."""

    def test_is_value_error(self) -> None:
        """The error subclasses ValueError."""
        assert issubclass(CoercionError, ValueError)

    def test_stores_char(self) -> None:
        """The offending character is stored, None for empty input."""
        assert CoercionError("?").char == "?"
        assert CoercionError().char is None

    def test_message_states_cause(self) -> None:
        """The message names the char, or emptiness when None."""
        assert "?" in str(CoercionError("?"))
        assert "empty" in str(CoercionError())
