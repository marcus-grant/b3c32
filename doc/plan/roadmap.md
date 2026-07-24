# Roadmap

Designed but demand-gated work.
Entries here have settled enough design to act on
but wait for the demand that justifies them.
Promotion moves an entry into TODO.

## Width tiers beyond 120

The contract certifies 120 bits only.
Wider 40-bit multiples are architecturally supported,
gated on per-width certification.

- Per-width pipeline vectors from the reference hex
- A prefix pair at the new width crossing the 64-byte block
- Certified set widened only with the vectors present
- Later, byte-aligned off-multiple widths:
  matching guaranteed through the penultimate symbol only,
  final symbol untrusted for pad bits

## PyO3 hybrid

First step of the Rust trajectory.
Rust core under the existing Python surface.

- The pytest suite runs against the Rust core through the binding,
  free conformance testing over the whole certified apparatus
- Rust replaces parts, then more, behind an unchanged Python API
- Consumers notice nothing but the pin bump

## Pure Rust implementation

The standalone crate.
Certification without Python anywhere in the loop:
each shippable artifact certifies in its own toolchain
against the shared vectors,
cross-language agreement transitive through the JSON,
never pairwise.

- Pure Rust tests reading the root vectors directory
- Cargo package from the rust subdirectory
- The codec CLI lands here as a single static binary,
  the port's first integration surface
- Audit gains a non-Rust-core digest leg:
  the official C implementation or an independent blake3,
  upgrading convenience vectors from binding-level
  to substrate-level confirmation

## Codec split

The codec earns its own module when the CLI work begins.

- Split core.py: codec functions into their own module,
  hashing and composition remaining
- CLI feature sketch, delivered by the pure Rust implementation:
  encode and decode anything, hash files, check codes

## Checksum layer

U and four non-alphanumerics are reserved
as the optional mod-37 check symbols.
Hand-written identifiers want transcription checking.

- Checksum append and verify functions
- Coerce gains its non-checksum declaration flag,
  unlocking U to V coercion per the decoder contract

## Continuous integration

- Gate command on push: ruff, pyright, pytest
- Audit script run against the frozen file
- Corrupted-vector red proof as a CI step, per fix 3
- Fuzz failure output surfaced prominently,
  artifact upload for permanence

## PyPI beyond first publication

The publish sequence in TODO covers v0.1.0.

- Version specifier consumption path documented for stakeholders
- Release cadence and changelog conventions

## Further language targets

Demand-gated, each certifying in its own toolchain
against the shared vectors.

- WASM transpilation of the Rust core
- JS native, or JS wrapping the WASM module, or both
- Go
- Each implementation ships its own smoke verification
  for its ecosystem's consumers
