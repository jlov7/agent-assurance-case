#!/usr/bin/env bash
# Validate OpenSSF security-insights.yml against the pinned upstream CUE schema.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SECURITY_INSIGHTS_FILE="${1:-$REPO_ROOT/security-insights.yml}"
SCHEMA_REF="5bc1ed0c6c7d0842293b47f1704b19288daeaa99"
CUE_VERSION="v0.14.1"
TMP_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

curl -fsSL \
  "https://raw.githubusercontent.com/ossf/security-insights/$SCHEMA_REF/spec/schema.cue" \
  -o "$TMP_DIR/security-insights.schema.cue"

go run "cuelang.org/go/cmd/cue@$CUE_VERSION" vet \
  -d '#SecurityInsights' \
  "$TMP_DIR/security-insights.schema.cue" \
  "$SECURITY_INSIGHTS_FILE"

echo "Security Insights: valid"
