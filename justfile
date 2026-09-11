# justfile
# Task runner for b3c32. Run from repo root; python recipes use
# uv --directory so nothing ever cd's into python/.

pyrun := "uv run --directory python"

set positional-arguments

# Strip a leading python/ from each arg so root-relative paths from
# shell completion reach the uv --directory python commands intact.
trim := 'for a in "$@"; do printf "%s " "${a#python/}"; done'

default:
    @just --list

# Install git hooks; once per clone
init:
    scripts/init-repo.sh

# Lint python
lint *args:
    {{pyrun}} ruff check $({{trim}})

# Type check and deterministic correctness checks on python
typecheck *args:
    {{pyrun}} pyright $({{trim}})

# Run the python suite; extra args pass through, e.g. just test -k name
test *args:
    {{pyrun}} pytest $({{trim}})

# Pre-commit gate: lint, typecheck, test, in that order
check: lint typecheck test

# Rederive every published vector with external tools only (b3sum, basenc, tr)
audit:
    scripts/audit-conformance-vectors.sh

# Gate plus external audit
certify: check audit

# Regenerate vectors/b3c32-conformance.json from hand-derived literals
vectors:
    uv run scripts/generate-conformance-vectors.py -o vectors/b3c32-conformance.json

