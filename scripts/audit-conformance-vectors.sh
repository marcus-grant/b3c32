#!/usr/bin/env bash
# scripts/audit-conformance-vectors.sh
#
# Independently derive the published conformance vectors using only external
# tools, and report any disagreement. Nothing from the certified
# implementation's code is in the loop: b3sum produces digests, coreutils
# basenc produces the bit-packing, and tr remaps the base32hex alphabet to
# Crockford.
#
# Caveat: b3sum binds the same Rust core as the python blake3 binding, so
# the digest leg is code-independent but not substrate-independent.
# Reference-input digests are separately certified by the pinned reference
# file; for convenience vectors this leg confirms binding-level wiring
# only. The encoding legs, basenc and tr, are genuinely foreign lineage.
#
# Usage: scripts/audit-conformance-vectors.sh [vector-file]
#
# Author: Marcus Grant
# Date: 2026-07-23
# License: Apache-2.0

set -euo pipefail

VECTORS="${1:-vectors/b3c32-conformance.json}"

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "missing: $1" >&2
    echo "  $2" >&2
    exit 1
  }
}

need b3sum "install with: apt install b3sum"
need basenc "part of coreutils: apt install coreutils"
need jq "install with: apt install jq"
need xxd "part of vim-common: apt install vim-common"

B3SUM_PIN="1.8.2"

b3sum_version="$(b3sum --version | cut -d' ' -f2)"
if [[ "$b3sum_version" != "$B3SUM_PIN" ]]; then
  msg="b3sum $b3sum_version does not match audit pin $B3SUM_PIN"
  if [[ "${B3C32_AUDIT_ALLOW_VERSION_DRIFT:-0}" == "1" ]]; then
    echo "warning: $msg" >&2
  else
    echo "$msg" >&2
    echo "  set B3C32_AUDIT_ALLOW_VERSION_DRIFT=1 to run anyway" >&2
    exit 1
  fi
fi

[[ -r "$VECTORS" ]] || {
  echo "cannot read vector file: $VECTORS" >&2
  exit 1
}

# base32hex is 0-9 then A-V; Crockford is 0-9 then A-Z skipping I, L, O, U.
# The two agree through H, so only values 18 and up are remapped.
crockford_from_hex() {
  xxd -r -p |
    basenc --base32hex |
    tr -d '=\n' |
    tr 'IJKLMNOPQRSTUV' 'JKMNPQRSTVWXYZ'
}

# Reference inputs are byte i is i mod 251, emitted as hex.
reference_input_hex() {
  local len="$1" i
  for ((i = 0; i < len; i++)); do
    printf '%02x' "$((i % 251))"
  done
}

fails=0
checked=0

report() {
  local label="$1" derived="$2" published="$3"
  checked=$((checked + 1))
  if [[ "$derived" == "$published" ]]; then
    printf 'ok    %-28s %s\n' "$label" "$derived"
  else
    printf 'FAIL  %-28s derived=%s published=%s\n' "$label" "$derived" "$published"
    fails=$((fails + 1))
  fi
}

# Encoder cases: encode the input bytes directly.
while IFS=$'\t' read -r input_hex encoded; do
  [[ -n "$encoded" ]] || continue
  derived=$(printf '%s' "$input_hex" | crockford_from_hex)
  report "encode ${input_hex:0:16}" "$derived" "$encoded"
done < <(jq -r '.cases[]
  | select(has("input_hex") and has("encoded"))
  | [.input_hex, .encoded] | @tsv' "$VECTORS")

# Pipeline cases given as literal bytes.
while IFS=$'\t' read -r input_hex digest_encoded; do
  [[ -n "$digest_encoded" ]] || continue
  digest=$(printf '%s' "$input_hex" | xxd -r -p | b3sum --no-names | cut -c1-30)
  derived=$(printf '%s' "$digest" | crockford_from_hex)
  report "pipeline ${input_hex:0:14}" "$derived" "$digest_encoded"
done < <(jq -r '.cases[]
  | select(has("input_hex") and has("digest_encoded"))
  | [.input_hex, .digest_encoded] | @tsv' "$VECTORS")

# Pipeline cases given by generated length.
while IFS=$'\t' read -r input_len digest_encoded; do
  [[ -n "$digest_encoded" ]] || continue
  input_hex=$(reference_input_hex "$input_len")
  digest=$(printf '%s' "$input_hex" | xxd -r -p | b3sum --no-names | cut -c1-30)
  derived=$(printf '%s' "$digest" | crockford_from_hex)
  report "pipeline len=$input_len" "$derived" "$digest_encoded"
done < <(jq -r '.cases[]
  | select(has("input_len") and has("digest_encoded"))
  | [.input_len, .digest_encoded] | @tsv' "$VECTORS")

echo
if ((fails > 0)); then
  echo "$fails of $checked disagreed" >&2
  exit 1
fi
echo "$checked checked, all agree"
