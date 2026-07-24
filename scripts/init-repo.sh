#!/usr/bin/env bash
# scripts/init-repo.sh
#
# One-time setup after cloning: symlink repo hooks into .git/hooks.
# Run from the repo root.

set -euo pipefail

[[ -d .git ]] || {
  echo "run from the repo root" >&2
  exit 1
}

ln -sf ../../scripts/commit-msg .git/hooks/commit-msg
echo "commit-msg hook linked"