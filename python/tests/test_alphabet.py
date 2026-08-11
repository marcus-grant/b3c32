# python/tests/test_alphabet.py
"""
Tests for the Crockford alphabet contract.
Author: Marcus Grant
Date: 2026-08-11
License: Apache-2.0
"""

import string

from b3c32.core import _CROCKFORD32


class TestCrockfordAlphabet:
    """Contract 4.4. The alphabet is pinned two independent ways, neither
    restating the module's literal.

    The first route rebuilds the alphabet from stdlib constants and the
    I, L, O, U exclusion rule, asserting the literal matches. The second
    pins it from spec facts alone: the digits block, the A and Z
    endpoints, the four skip transitions, and strict ascent. The routes
    share no source, so a typo in the literal fails the first and a
    wrong exclusion rule fails the second.
    """

    def test_matches_rule_construction(self):
        """The literal equals digits followed by uppercase letters with
        I, L, O, U removed, built from stdlib constants."""
        alphanum = string.digits + string.ascii_uppercase
        assert _CROCKFORD32 == "".join(c for c in alphanum if c not in "ILOU")

    def test_length_is_32(self):
        """The alphabet is exactly 32 symbols, one per 5-bit value."""
        assert len(_CROCKFORD32) == 32

    def test_symbols_unique(self):
        """No symbol repeats, every 5bit value maps to a distinct character."""
        assert len(set(_CROCKFORD32)) == 32

    def test_excludes_ambiguous_letters(self):
        """No I,L,O,U appear: 1st 3 ambiguous visually to 1,0; U reserved to checksum"""
        assert not any(c in _CROCKFORD32 for c in "ILOU")

    def test_digits_block(self):
        """First 10 symbols are digits 0 to 9 without stdlib string helpers."""
        assert _CROCKFORD32[:10] == "".join(str(n) for n in range(10))

    def test_letters_start_after_digits(self):
        """A appears at 10, after digits block, and Z at end index of 31."""
        assert _CROCKFORD32[10] == "A"
        assert _CROCKFORD32[31] == "Z"

    def test_skip_transitions_positional(self):
        """Skips at HJ, KM, NP, TV, pinning which are omitted in alphanum sequence."""
        assert _CROCKFORD32.index("H") + 1 == _CROCKFORD32.index("J")
        assert _CROCKFORD32.index("K") + 1 == _CROCKFORD32.index("M")
        assert _CROCKFORD32.index("N") + 1 == _CROCKFORD32.index("P")
        assert _CROCKFORD32.index("T") + 1 == _CROCKFORD32.index("V")

    def test_ordering_monotonic(self):
        """Digits 0-9 occupy indices 0-9 and letters ascend thereafter,
        so lexical order of encoded strings matches bit order."""
        previous_symbol = _CROCKFORD32[10]
        for current_symbol in _CROCKFORD32[11:]:
            msg = f"Alphabet order not monotonic: {previous_symbol} >= {current_symbol}"
            assert current_symbol > previous_symbol, msg
            previous_symbol = current_symbol
