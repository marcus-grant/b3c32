# python/tests/test_package.py
"""
Tests for the b3c32 package public surface.
Author: Marcus Grant
Date: 2026-07-24
License: Apache-2.0
"""

import b3c32

_PUBLIC_INTERFACES = {
    "UncertifiedWidthError",
    "coerce_crockford_b32",
    "decode_crockford_b32",
    "encode_crockford_b32",
    "hash_b32",
    "hash_digest",
}


class TestPublicSurface:
    """The package manifest is the contract surface, exactly."""

    def test_all_is_exact(self) -> None:
        """__all__ holds exactly the six contract names."""
        assert set(b3c32.__all__) == _PUBLIC_INTERFACES

    def test_all_no_dupes(self) -> None:
        """__all__ holds no duplicate names."""
        assert len(set(b3c32.__all__)) == len(b3c32.__all__)

    def test_all_names_resolve(self) -> None:
        """Every name in __all__ is an attribute of the package."""
        for name in b3c32.__all__:
            assert hasattr(b3c32, name), f"__all__ names missing attribute {name}"
