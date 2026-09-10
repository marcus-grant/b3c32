# TODO

Imminent work, ordered by priority.
The eight fix entries following streaming are the founding sequence:
findings from the pre-extraction adversarial review of the conformance tooling,
ordered by severity.
Each entry records the finding and its settled design where discussion resolved one.
Resolved entries are deleted, not marked resolved.

## Streaming: whole-file buffering blocks large inputs

`hash_b32` takes materialised bytes,
so peak memory scales with input size.
Scout routinely hashes multi-gigabyte files and tar archives near 100GB;
those cannot be hashed at all.
normpic records this as blocking its own streaming entry
and gating remote sourcing entirely.
Settled design:

- Chunk-consuming core holds hasher state, slicing, encoding,
  progress throttle and completion guarantee; internal for now
- Stream-accepting entry point drives a sync read loop over the core
- Path-accepting entry point opens binary, delegates, closes on both paths
- Opt-in push progress via `on_progress`, receiving cumulative bytes consumed
- Total bytes never appears in the signature; only the caller knows one
- `progress_interval` in seconds, minimum spacing, not exact
- Completion callback fires unconditionally, once with zero on an empty file
- Errors propagate; an interrupted read never yields a digest
- Core stays sync and blocking; `async` is a later driver over the same core

## CLI: no out-of-band way to produce hashes

Scout needs hashes fed into its SQLite manifests by hand
during workflow exploration,
and its hash column needs independent sanity checking.
Depends on the path and stream entry points.
Settled design:

- `b3c32sum`:
  - console script,
  - argparse only,
  - single package
- `Coreutils` output shape:
  - `-n/--no-name` prints the hash alone
  - `-w/--width-bits` and `-W/--width-symbols`,
    - mutually exclusive,
    - default 120 bits;
      - refuses uncertified widths
  - `stdin` on no arguments or `-`,
    - printed as `-` in the filename column
  - `-T/--total-bytes` supplies a stdin progress total; error with a path
  - `-c` takes one expected hash; normalized both sides, strict length
- Progress automatic on `TTY` `stderr`,
  - `--progress` and `--no-progress` override
- Exit codes from a declared map:
  - 0 success,
  - 1 mismatch,
  - 2 usage error,
  - 3 unreadable input
- Deferred:
  - Sums-file check mode.
    - When it lands,
      - `-c` disambiguates by filesystem first,
      - hash shape second
  - Prefix matching in check mode

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

## `Async`: streaming core has no `async` driver

The streaming entry point drives a sync read loop,
so an `async` consumer must buffer whole inputs to hash them,
which defeats the memory bound streaming exists to provide.
depo hashes Starlette uploads before they are committed to the store
and never holds a path;
its ingestion pipeline assumes materialised bytes throughout
and needs rework before it can consume this.
Settled design:

- Additive thin driver over the chunk-consuming core from the streaming entry
- Differs from the sync loop by the await; nothing below the loop forks
- Digest, slicing, and encoding stay shared, so results cannot diverge
- Document that the sync reader under a `Starlette` `UploadFile` is the file object,
  not the `UploadFile`, whose read is a coroutine
- Open: whether the surface accepts `async` iterators as well as `async` readers

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
