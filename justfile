# justfile
# Task runner for b3c32. Run from repo root; python recipes use
# uv --directory so nothing ever cd's into python/.

pyrun := "uv run --directory python"

default:
    @just --list

# Install git hooks; once per clone
init:
    scripts/init-repo.sh

# Lint python
lint *args:
    {{pyrun}} ruff check {{args}}

# Type check python
typecheck *args:
    {{pyrun}} pyright {{args}}

# Run the python suite; extra args pass through, e.g. just test -k name
test *args:
    {{pyrun}} pytest {{args}}

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

