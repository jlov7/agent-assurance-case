#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REQUIREMENTS="$ROOT/verifier/requirements.txt"
LOCKFILE="$ROOT/verifier/requirements.lock.txt"
TEMP_ROOT="$(mktemp -d)"

cleanup() {
  rm -rf "$TEMP_ROOT"
}
trap cleanup EXIT

normalize_header() {
  sed -E \
    -e 's#uv pip compile .*requirements.txt --generate-hashes#uv pip compile <runtime-requirements> --generate-hashes#' \
    -e 's# -o .*$# -o <runtime-lockfile>#'
}

uv pip compile "$REQUIREMENTS" --generate-hashes -o "$TEMP_ROOT/requirements.lock.txt" >/dev/null
normalize_header < "$LOCKFILE" > "$TEMP_ROOT/committed.normalized"
normalize_header < "$TEMP_ROOT/requirements.lock.txt" > "$TEMP_ROOT/generated.normalized"
diff -u "$TEMP_ROOT/committed.normalized" "$TEMP_ROOT/generated.normalized"

uv run --with-requirements "$LOCKFILE" --with pip-audit pip-audit

echo "Runtime dependency lock: valid"
