# TODO

Imminent work, ordered by priority.
The eight fix entries following streaming are the founding sequence:
findings from the pre-extraction adversarial review of the conformance tooling,
ordered by severity.
Each entry records the finding and its settled design where discussion resolved one.
Resolved entries are deleted, not marked resolved.

## Async: streaming core has no async driver

The streaming entry point drives a sync read loop,
so an `async` consumer must buffer whole inputs to hash them,
defeating the memory bound streaming exists to provide.
depo hashes Starlette uploads before they are committed
and never holds a path;
its ingestion pipeline assumes materialised bytes throughout
and needs rework before it can consume this.
Settled design:

- Additive thin driver over the chunk-consuming core
- Differs from the sync loop by the await;
  - nothing below the loop forks
- So results can't diverge:
  - Digest, slicing, and encoding stay shared
- Document that the sync reader under a `Starlette` `UploadFile` is the file object,
  - not the `UploadFile`,
  - whose read is a coroutine
- Open: whether the surface accepts `async` iterators as well as readers

## Fix 4: Verifier anchor test discards its expected values

`test_matches_known_vectors` compares encoder against verifier
and throws away the vector literals,
contradicting its docstring's independence claim.

Settled design:

- Assert the verifier reproduces the literal expected values directly

## Fix 5: Emitted vector file carries no provenance

The generator writes only a comment and cases.
The doc promises bumped provenance with nothing to bump.
Byte-identical regeneration works only because nothing varies.

Settled design:

- Add a fourth convenience vector, 0xaa repeated 1025 times,
  trivially constructible in any language,
  crossing the blake3 chunk boundary through the full pipeline
- Add pinned provenance fields:
  reference tag and commit, reference file SHA-256,
  generator identity, schema version
- No timestamps, so regeneration stays byte-identical
- Per-case derivation marker distinguishing hand-held literals
  from derived cases
- Widen reference-input pipeline coverage to every case
  in the reference file,
  derived cases marked as such,
  the five existing staying as asserted hand-held literals
- Document the vector file schema as a mini-spec in doc

## CLI: b3c32sum beyond the minimum

Default output is the code alone as shipped;
the coreutils `CODE  NAME` shape is not.
Which is the default, and the flag direction that follows,
is decided when named output lands.

- Coreutils output shape:
  - `CODE  NAME` lines, stdin printed as `-`
  - `-w/--width-bits` and `-W/--width-symbols`,
    - mutually exclusive,
    - default 120 bits;
      - refuses uncertified widths
  - `-c` takes one expected hash; normalized both sides, strict length
- Progress automatic on `TTY` `stderr`,
  - `--progress` override
- Exit code 1 for mismatch, once `-c` exists
- Sub-MiB sizes print as `0.0/0.0 MiB`; pick a unit ladder
- Deferred:
  - Sums-file check mode.
    - When it lands,
      - `-c` disambiguates by filesystem first,
      - hash shape second
  - Prefix matching in check mode

## Fix 6: Generator never verifies the reference file pin

Only the test suite asserts the pinned SHA-256.
A generation run against a swapped file fails
only by comparison against the implementation's own hasher,
the pattern the governing rule forbids.

Settled design:

- Generator asserts the reference file's SHA-256 before deriving anything

## Fix 7: Alignment guard test uses uniform bytes

The positive half of `test_prefix_requires_aligned_width`
passes for any encoder emitting uniform output on uniform input,
so it barely discriminates.

Settled design:

- Use non-uniform data, the reference-input pattern,
  so both halves discriminate

## Fix 8: Nonzero-pad decode acceptance untested

Strict decode silently accepts codes
whose discarded trailing bits are nonzero.
The doc acknowledges the asymmetry;
no test pins the behavior,
so a future rejection change lands with no red.

Settled design:

- Pin the acceptance with a test naming the documented rationale

## Naming cutover: noun_from_source

New surface uses `noun_from_source`: `digest_from_chunks`,
`digest_from_stream`, `digest_from_path`, and the `code_from_*`
counterparts. `hash_digest` and `hash_b32` are the retained legacy
names, equivalent to `digest_from_bytes` and `code_from_bytes`.
Cutover is staged on the Rust port: the pyo3 hybrid is where the
deprecation flags on the legacy names start; completion of the Rust
port is the cutover that deletes deprecated public names. Until then
no deprecation warnings are emitted.

## Chores from the streaming work

- Anchor `scripts/generate-conformance-vectors.py` and
  `scripts/audit-conformance-vectors.sh` on their own location so the
  `just vectors` and `just audit` recipes drop their path arguments.
- Generator docstring still says "depo's implementation".
- Rename `_reference_input` and `_chunked` in `tests/vectors.py` to
  public names; they are shared across test modules.
- Comment `REFERENCE_ENCODED_VECTORS` and `CONVENIENCE_ENCODED_VECTORS`
  in `tests/vectors.py` with their contract clauses.
- `test_codec.py` may split encode from decode if legibility suffers.

## CI and publish gating

Nothing mechanically checks a tagged commit. The full gate is manual,
so the publish workflow will happily build and publish a commit that
never passed it. Publication is irreversible, which makes this the
one place manual discipline is not enough.

- Bump action versions off Node 20: checkout and upload-artifact
  to v5, setup-uv to v6
- Test job in the publish workflow: ruff, pyright, pytest against the
  checkout, with both publish jobs depending on it
- Tests on push and PR, not only at publish, resolving the standing
  no-CI hazard
- Audit script in CI needs b3sum pinned in the runner, so it rides
  later or gets its own entry

## Conformance doc sharpening

Clarity edits settled in discussion, riding with the fixes above.

- Lead with the three-claim certification statement:
  correct use of blake3, correct low-pad bitstream Crockford encoding,
  correct composition of the two,
  each mapped to its best available oracle
- State the oracle upgrade procedure:
  new tag, re-fetch, re-ratify hash, regenerate,
  full suite green, provenance bump
- State that no authored Crockford reference encoder exists,
  so encoding conformance is independent-axis agreement,
  the strongest available claim
- State that composition correctness is inherited
  from the two certified components,
  with pipeline vectors as regression pins, not proof
- Clarify fuzz graduation:
  found failures enter the vector file via the fix PR
  as hand-held literals with fuzz-found provenance
- Blake3 structure subsection rides with fix 1,
  as already noted there
- Width section rewrite to certified-tier language,
  including retiring the off-ladder term,
  rides wherever the certified-width gate lands

## v0.1.0 milestone

MVP marker, publication having moved pre-MVP.
Tag v0.1.0 when every entry above is resolved.
Routine tag-and-publish through the wired machinery.
