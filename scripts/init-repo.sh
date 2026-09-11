#!/usr/bin/env bash
# scripts/init-repo.sh
#
# One-time setup after cloning: point git at the tracked hooks directory.
# Run from the repo root.

set -euo pipefail

[[ -d .git ]] || {
  echo "run from the repo root" >&2
  exit 1
}

git config core.hooksPath scripts/hooks
echo "hooks path set to $(git config core.hooksPath)"

