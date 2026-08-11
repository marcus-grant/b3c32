# b3c32

Compact, hand-writable, prefix-matchable XOF hashes and identities for
anything.

b3c32 defines a content addressing scheme and certifies implementations
of it. Codes are unkeyed BLAKE3 sliced on 40-bit boundaries, encoded as
low-pad bitstream Crockford Base32. The result is short enough to write
by hand, unambiguous enough to read aloud, and prefix-matchable so a
truncated code still resolves.

The contract artifacts are language neutral and live at the repo root.
Implementations live in per-language directories and are certified
against the same frozen vectors.

## Layout

- [doc/](./doc/README.md) contract and design documents
- [vectors/](./vectors/) frozen conformance vectors, the contract artifacts
- [scripts/](./scripts/) vector generation and external audit tooling
- [python/](./python/README.md) reference implementation, a uv project;
  - installs from PyPI as `b3c32`, or from git with this subdirectory

## Consuming

Install from PyPI:

    uv add b3c32

Or from git, pinning a tag, when you need an unreleased commit:

    [project]
    dependencies = ["b3c32"]

    [tool.uv.sources]
    b3c32 = { git = "https://github.com/marcus-grant/b3c32", subdirectory = "python", tag = "v0.0.2" }

Pin an exact version either way. The project is pre-1.0 and no
compatibility policy is in force, so any release may change the
contract. Call verify_conformance in your own suite to learn when it
does:

    def test_b3c32_contract():
        from b3c32 import verify_conformance
        verify_conformance()

One test, and it raises AssertionError naming the failed claim. The
normative statement of what is being conformed to is in
[doc/conformance.md](./doc/conformance.md).

## Status

Pre-release. The Python implementation passes the extracted conformance
suite. Certification hardening is in progress; see the planning
documents in doc. Current certified width: 120 bits.
