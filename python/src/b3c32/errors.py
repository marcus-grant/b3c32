# python/src/b3c32/errors.py
"""
Exception types for b3c32.
Author: Marcus Grant
Date: 2026-07-24
License: Apache-2.0
"""


class UncertifiedWidthError(ValueError):
    """Raised when a requested digest width is not in the certified set.

    Subclasses ValueError so naive callers still catch it; distinct so
    consumer smoke tests can assert the gate survived an upgrade.
    """

    def __init__(self, bits: int) -> None:
        self.bits = bits
        super().__init__(f"digest width {bits} bits is not certified by contract")


class CoercionError(ValueError):
    """Raised when user-supplied code cannot be coerced to canonical form.

    Carries the offending character, or None when the input was empty
    after normalization.
    """

    def __init__(self, char: str | None = None) -> None:
        self.char = char
        if char is None:
            msg = "cannot coerce input, empty after normalization"
        else:
            msg = f"cannot coerce input, offending char: {char}"
        super().__init__(msg)
