#!/bin/bash
# Generate test patterns for hash_full_b32 verification
#
# Usage: $0 [length_bytes] [pattern]
#   length_bytes: Number of bytes to generate (default: 512)
#   pattern:      zeros|ones|aa|55|sequential|walker|all (default: all)
#
# Examples:
#   ./generate-test-patterns.sh              # 128 bytes, all patterns
#   ./generate-test-patterns.sh 100          # 100 bytes, all patterns
#   ./generate-test-patterns.sh 515 zeros    # 128 bytes of zeros
#   ./generate-test-patterns.sh 1024 aa      # 1024 bytes of 0xAA
#
# It is important to have independent verification of the hash function results
# To do that with long patterns becomes difficult, so this script generates them.
#
# These bit patterns produce tricky cases for hash functions
#
# Author: Marcus Grant
# Created: 2026-01-17

# Assign parameters with defaults
LENGTH="${1:-128}"
PATTERN="${2:-all}"

# Validate length is a positive integer
if ! [[ "$LENGTH" =~ ^[0-9]+$ ]] || [[ "$LENGTH" -eq 0 ]]; then
  echo "Error: length must be a positive integer" >&2
  exit 1
fi

# Calculate hex chars needed (2 hex chars per byte)
HEX_CHARS=$((LENGTH * 2))

# For walker pattern, calculate repetitions (5 bytes per unit)
WALKER_REPS=$(((LENGTH + 4) / 5))

# Handle each named pattern
case "$PATTERN" in
zeros)
  printf 'hex:%0*d' "$HEX_CHARS" 0
  ;;
ones)
  printf 'hex:'
  printf 'ff%.0s' $(seq 1 "$LENGTH")
  ;;
aa)
  printf 'hex:'
  printf 'aa%.0s' $(seq 1 "$LENGTH")
  ;;
55)
  printf 'hex:'
  printf '55%.0s' $(seq 1 "$LENGTH")
  ;;
sequential)
  printf 'hex:'
  for i in $(seq 0 $((LENGTH - 1))); do
    printf '%02x' $((i % 256))
  done
  ;;
walker)
  # 5-bit boundary walker: 0x21 0x08 0x42 0x10 0x84 repeating
  # Truncate to exact length requested
  printf 'hex:'
  printf '2108421084%.0s' $(seq 1 "$WALKER_REPS") | head -c "$HEX_CHARS"
  ;;
all)
  echo "=== Test patterns ($LENGTH bytes each) ==="
  echo
  for p in zeros ones aa 55 sequential walker; do
    echo "--- $p ---"
    $0 "$LENGTH" "$p"
    echo
    echo
  done
  ;;
*)
  echo "Usage: $0 [length_bytes] [pattern]" >&2
  echo "  length_bytes: Number of bytes to generate (default: 515)" >&2
  echo "  pattern:      zeros|ones|aa|55|sequential|walker|all (default: all)" >&2
  exit 1
  ;;
esac
