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
- [python/](./python/) reference implementation, a uv project

## Status

Pre-release. The Python implementation passes the extracted conformance
suite. Certification hardening is in progress; see the planning
documents in doc. Current certified width: 120 bits.
