# python/tests/test_errors.py
"""
Tests for b3c32 exception types.
Author: Marcus Grant
Date: 2026-07-24
License: Apache-2.0
"""

from b3c32.errors import UncertifiedWidthError


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
