# Handoff

This document is both a template and a living handoff. Sections marked
[static] stay across all handoffs. Sections marked [per-session] get
replaced each time.

## How to use this document [static]

Read by a collaborator at the start of each session. The collaborator
has NO filesystem, sandbox, or execution environment relevant to this
project. All commands are printed as text for the user's shell, usually
piped to their `cc` clipboard command. The collaborator never runs
project commands itself and never assumes an edit landed: disk state is
verified by grep or diff through the user before it is trusted.

At session start: read this document in full; follow links to planning
docs only as needed.

Before ending a session: rewrite per-session sections fresh; carry
static sections forward in full with any updates; trim completed
planning items; record deferrals in the planning docs, not only here;
output the finished handoff as one complete markdown fence the user
copies to persist.

## Project identity [static]

b3c32: compact, hand-writable, prefix-matchable XOF hashes and
identities for anything. Unkeyed BLAKE3 sliced on 40-bit boundaries,
low-pad bitstream Crockford Base32. The repo root holds the
language-neutral contract (vectors, audit script, conformance doc);
implementations live in per-language subdirectories, python first.
The conformance doc is normative: where implementation and doc
conflict, the doc wins. Consumers (depo, normpic, scout) pin git tags
and call verify_conformance in their suites.

## Working agreement [static]

- One thing per exchange: one command, one decision, one task.
- Stub-first TDD: the collaborator provides stubs (signatures,
  docstrings, spec comments, bodies raising NotImplementedError); the
  user writes test bodies and implementations. Red confirmed before
  green; blue refactors keep green. Implementations only on explicit
  request.
- Full gate before every commit:
  uv run ruff check, uv run pyright, uv run pytest, in that order.
- Discuss before scope expansion; deferrals announced at commit points,
  not mid-edit.
- Edit guidance names files and anchors in prose, never line numbers.
  When edit friction rises, deliver the whole file instead.
- Verification commands stay minimal: exit codes over line dumps.
- Merges happen on GitHub, never via CLI chains.
- Nvim hazard: ghost buffers and stale swaps have repeatedly produced
  confirmed-but-unsaved edits. Never recover a swap; delete it. Verify
  disk before trusting any edit.

## Conventions [static]

- Commit format: prefix (Ft, Fix, Ref, Doc, Pln, Chr, Tst), subject
  under 50 chars, dash-list body, each bullet a single line under 72,
  first word capitalized. The commit-msg hook enforces this; run
  scripts/init-repo.sh once per clone.
- Prose docs use semantic line breaks: natural fragments, 80 target,
  88 grace. ASCII-128 only, no em-dashes, headers not bold markers.
- READMEs link only deeper; dead links are intentional todo markers.
- Resolved planning entries are deleted, not marked resolved.
- Python module headers: path comment, docstring with Author, Date,
  Revisions (added at first revision), License.
- Python commands from repo root: uv run --directory python, or
  UV_PROJECT=python exported for tab-completable paths.

## Work map [static]

- doc/plan/TODO.md: fixes 4-8, conformance doc sharpening, publish
  sequence. The publish sequence is the MVP finale; v0.1.0 tags and
  publishes to PyPI only when TODO is empty.
- doc/plan/roadmap.md: demand-gated work in sequence order.
- doc/plan/unplanned.md: P-tier idea intake.

## Known standing hazards [static]

- Audit count assertion assumes no case matches two legs; fix 5's
  widening must revisit if combined cases appear.
- Smoke falsifiability tests bind to verify_conformance's internal call
  order; reordering the body reorders the patches.
- Dev-invocation docs need a proper home (development.md or
  CONTRIBUTING) as contributor docs grow.

## Orientation [per-session]

Rewrite fresh each session: date; committed work this session in order
with one-line descriptions and branch; in-progress work and deliberate
scope decisions; the immediate next action and its branch.

## Known issues [per-session]

Rewrite fresh each session: active bugs or rough edges with locations;
deferrals made this session cross-referenced to their planning doc;
"none open" is a valid state.
