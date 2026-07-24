# TODO

Imminent work, ordered by priority.
The first eight entries are the founding sequence:
findings from the pre-extraction adversarial review of the conformance tooling,
ordered by severity.
Each entry records the finding and its settled design where discussion resolved one.
Resolved entries are deleted, not marked resolved.

## Fix 1: Prefix integrity theater

No assertion inspects any shipped-hasher byte past index 14,
so the cross-64-byte XOF property the scheme exists for is never tested.
Confirmed with the original implementer: `_hash_digest` was reused
where full-width comparison was intended, no deliberate scoping.

Settled design:

- `test_reference_output_full_equality` replaces the reference prefix test:
  shipped hasher reproduces all 131 bytes of the reference extended output,
  a width-independent engine check crossing the 64-byte XOF block
- `test_shipped_build_is_prefix_consistent` keeps non-reference inputs
  but compares short length 70 against long length 131,
  so the compared region itself crosses the block boundary
- The 120-bit slice claim stays where it lives,
  in `test_digest_matches_reference_prefix`
- Conformance doc gains a subsection under Assertion classes
  covering both blake3 structure axes:
  input-side chunk boundaries justifying the reference lengths,
  output-side 64-byte XOF blocks requiring assertions past byte 64

## Certified width gate

Not a review finding, a prerequisite for consumer integration.
The extracted API is 120-bit only by construction;
the parametric API must fail loudly on any width it does not certify,
including capabilities depo's shortcode module never had.

Settled design:

- Public `hash_digest(data, bits)` and `hash_b32(data, bits)`,
  `bits` required with no default,
  consumers own their width constant
- `_CERTIFIED_BITS = frozenset({120})`,
  membership checked before hashing,
  private with a read-only accessor if tooling wants it
- Distinct `UncertifiedWidthError`, not a bare ValueError,
  so consumer smoke tests can assert the gate survived an upgrade
- Certified width tests parametrize over the certified set,
  so widening the set without per-width vectors fails red automatically
- Decode goes public as `decode_crockford_b32`,
  `canonicalize_code` renamed `coerce_crockford_b32`,
  the LSP silencer line dies

## Fix 2: Audit digest leg shares blake3's Rust core

b3sum and the python blake3 binding wrap the same Rust implementation,
so the audit's digest leg is same-substrate, not independent.
Convenience vectors get falsely upgraded to externally confirmed.
b3sum's version is neither pinned nor asserted.

Settled design:

- State the shared-core caveat in the script header
- Keep convenience-vector labeling honest in doc and vector file
- Pin and assert b3sum's version in the script's need checks
- A non-Rust-core digest leg is roadmap material, not this fix

## Fix 3: Auditor can pass vacuously

Zero jq matches yields zero checked, all agree, exit 0.
The empty-input vector is silently skipped by the empty-string guard.
Nothing proves the auditor goes red on a corrupted file.

Settled design:

- Assert checked count equals the case count read from the file
- Handle the empty-encoded case explicitly instead of skipping it
- Add a self-test mode or CI step that corrupts one value
  and asserts exit 1
- Suite asserts the frozen file's cases include exactly
  the hand-held literal set,
  so generator-versus-test drift fails every run,
  not only at regeneration

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

## Publish sequence

MVP finale.
The tag v0.1.0 is cut and published only when every entry above is resolved.

- Metadata polish: readme as long description, classifiers, license file
- PyPI trusted publisher wired to GitHub Actions,
  publishing on tags only
- Cut v0.1.0, first published tag,
  claiming the name at the moment the artifact deserves it
- Consumers may pin git tags before this;
  PyPI is the post-MVP consumption path
