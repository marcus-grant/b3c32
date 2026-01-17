#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./hash-b32.sh 'Hello, World!'     # hashes UTF-8 bytes of the text (no newline)
#   ./hash-b32.sh 'hex:0000000000'    # hashes raw bytes given as hex
#   NOTE: echo appends a newline and some characters need escaping

if [[ $# -ne 1 ]]; then
  echo "usage: $0 '<text>' | 'hex:<hex-bytes>'" >&2
  exit 2
fi

need() { command -v "$1" >/dev/null 2>&1 || {
  echo "missing: $1" >&2
  exit 1
}; }
need b2sum
need basenc
need xxd
need awk
need tr
need printf

arg="$1"

# get input bytes on stdin
if [[ "$arg" == hex:* ]]; then
  hex="${arg#hex:}"
  printf '%s' "$hex" | tr -d ' \n' | xxd -r -p
else
  printf '%s' "$arg"
fi |
  b2sum -l 120 | awk '{print $1}' |
  {
    read -r hexhash
    printf '%s\n' "$hexhash" # 1) hex line (stdout)
    printf '%s' "$hexhash" | # 2) same hex, no newline, into encoder
      xxd -r -p |
      basenc --base32hex |
      tr -d '=\n' |
      tr 'IJKLMNOPQRSTUV' 'JKMNPQRSTVWXYZ'
    echo
  }
