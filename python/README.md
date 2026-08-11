# b3c32 (Python)

Compact, hand-writable, prefix-matchable XOF hashes and identities for
anything.

This is the Python implementation of b3c32, and until otherwise stated
it is the reference implementation: the contract artifacts at the
project root are certified against it, and other language
implementations are certified against the same frozen vectors. That
status is expected to change once a native Rust implementation exists.

Codes are unkeyed BLAKE3 sliced on 40-bit boundaries, encoded as
low-pad bitstream Crockford Base32. The result is short enough to write
by hand, unambiguous enough to read aloud, and prefix-matchable so a
truncated code still resolves.

## Use

```python
from b3c32 import hash_b32

code = hash_b32(b"hello", 120)
```

Width is in bits. 120 is the current certified width. This is not a
ceiling on usefulness: slice the returned code at any multiple of 40
bits, which is 5 bytes or 8 characters, and the short form is a true
string prefix of the long one. Store the full code, index a prefix.

The package also exports `hash_digest` for raw digest bytes, the codec
functions `encode_crockford_b32`, `decode_crockford_b32`, and
`coerce_crockford_b32`, the alphabet as `CROCKFORD32_ALPHABET`, and the
error types `UncertifiedWidthError` and `CoercionError`.

## Consuming

Pin an exact version. The project is pre-1.0 and no compatibility
policy is in force, so any release may change the contract. Call
`verify_conformance` in your own suite to learn when it does:

```python
from b3c32 import verify_conformance

def test_b3c32_contract():
    verify_conformance()
```

It raises AssertionError naming the failed claim. Its scope is drift
detection through the public API at the certified width; deep
certification is this project's own suite against the pinned BLAKE3
reference vectors.

## Status

Pre-release. Certification hardening is in progress. The full scheme
definition, the normative conformance contract, and the frozen vectors
live at the project root:
https://github.com/marcus-grant/b3c32