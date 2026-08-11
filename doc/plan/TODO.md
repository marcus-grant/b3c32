# TODO

Imminent work, ordered by priority.
The first eight entries are the founding sequence:
findings from the pre-extraction adversarial review of the conformance tooling,
ordered by severity.
Each entry records the finding and its settled design where discussion resolved one.
Resolved entries are deleted, not marked resolved.

## Publish to PyPI pre-MVP

Decided after NormPic's blind-integration friction: index installation
dissolves the subdirectory and sources-block tribal knowledge, so
publication pulls forward from the MVP finale. Dev-status classifiers
keep the artifact honest about its pre-MVP state.

- License file, classifiers with development status, readme as long
  description pointing at the root README
- Trusted publisher wired to a GitHub Action, publishing on tags only
- Bump version, tag 0.0.2 containing the alphabet export, publish
- NormPic and depo may swap to the index dependency at their next bump
- License file, classifiers with development status, readme as long
  description pointing at the root README
- Root README gains a Consuming section: index install as primary,
  the git sources block with subdirectory and tag rev as fallback,
  the tag-pin convention, the one-test verify_conformance pattern
- Python layout bullet gains a subdirectory-install pointer
- Trusted publisher wired to a GitHub Action, publishing on tags only
- Bump version, tag 0.0.2 containing the alphabet export, publish
- NormPic and depo may swap to the index dependency at their next bump

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
