# python/tests/test_package.py
"""
Tests for the b3c32 package public surface.
Author: Marcus Grant
Date: 2026-07-24
License: Apache-2.0
"""

import importlib

import pytest

import b3c32

_PUBLIC_INTERFACES = {
    "CERTIFIED_BITS",
    "CROCKFORD32_ALPHABET",
    "UncertifiedWidthError",
    "CoercionError",
    "coerce_crockford_b32",
    "decode_crockford_b32",
    "digest_from_chunks",
    "digest_from_path",
    "digest_from_stream",
    "code_from_chunks",
    "code_from_stream",
    "code_from_path",
    "encode_crockford_b32",
    "hash_b32",
    "hash_digest",
    "verify_conformance",
}

_HOME_MODULES = {
    "CERTIFIED_BITS": "b3c32.digest",
    "CROCKFORD32_ALPHABET": "b3c32.codec",
    "coerce_crockford_b32": "b3c32.codec",
    "decode_crockford_b32": "b3c32.codec",
    "encode_crockford_b32": "b3c32.codec",
    "hash_digest": "b3c32.digest",
    "hash_b32": "b3c32.scheme",
    "code_from_chunks": "b3c32.scheme",
    "code_from_stream": "b3c32.scheme",
    "code_from_path": "b3c32.scheme",
    "digest_from_chunks": "b3c32.stream",
    "digest_from_stream": "b3c32.stream",
    "digest_from_path": "b3c32.stream",
    "UncertifiedWidthError": "b3c32.errors",
    "CoercionError": "b3c32.errors",
    "verify_conformance": "b3c32.smoke",
}


class TestPublicSurface:
    """The package manifest is the contract surface, exactly."""

    def test_all_is_exact(self) -> None:
        """__all__ holds exactly the contract names."""
        assert set(b3c32.__all__) == _PUBLIC_INTERFACES

    def test_all_no_dupes(self) -> None:
        """__all__ holds no duplicate names."""
        assert len(set(b3c32.__all__)) == len(b3c32.__all__)

    def test_all_names_resolve(self) -> None:
        """Every name in __all__ is an attribute of the package."""
        for name in b3c32.__all__:
            assert hasattr(b3c32, name), f"__all__ names missing attribute {name}"


class TestModuleStructure:
    """Each public name has exactly one home module; the package re-exports it."""

    def test_home_modules_cover_public_surface(self) -> None:
        """_HOME_MODULES keys are exactly the public names."""
        assert set(_HOME_MODULES) == _PUBLIC_INTERFACES

    def test_names_originate_in_home_module(self) -> None:
        """The package attribute is the same object as the home module's."""
        for name, home in _HOME_MODULES.items():
            module = importlib.import_module(home)
            msg = f"{name} is not re-exported from {home}"
            assert getattr(b3c32, name) is getattr(module, name), msg

    def test_core_module_is_gone(self) -> None:
        """b3c32.core no longer exists."""
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module("b3c32.core")
