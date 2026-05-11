#!/usr/bin/env bash
# Publication-readiness gate for the Agent Assurance Case (AAC) v0.2-candidate.2 artifact.
#
# Run this before pushing to the public GitHub repo. The gate checks:
#   1. The v0.1 leftover files are not present (they would weaken the public artifact).
#   2. The test suite passes with 10/10 tests.
#   3. Each of the three bundled examples verifies cleanly.
#   4. The bug-1 regression (silent signature skip) is still caught.
#   5. The schema URI in SPEC.md matches the schema file shipped.
#   6. The verifier source contains the V7 hardening hooks.
#
# Exit code 0 = ready to publish. Non-zero = stop and fix the listed item.

set -uo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

PASS=0
FAIL=0
RESULTS=()

check() {
  local name="$1"
  local ok="$2"
  local detail="${3:-}"
  if [[ "$ok" == "ok" ]]; then
    RESULTS+=("  [OK  ] $name${detail:+ — $detail}")
    PASS=$((PASS + 1))
  else
    RESULTS+=("  [FAIL] $name${detail:+ — $detail}")
    FAIL=$((FAIL + 1))
  fi
}

# 1. v0.1 leftover files must not be present.
if [[ -e "examples/minimal-pass.json" || -e "schemas/agent-assurance-case-v0.1.schema.json" ]]; then
  leftovers=()
  [[ -e "examples/minimal-pass.json" ]] && leftovers+=("examples/minimal-pass.json")
  [[ -e "schemas/agent-assurance-case-v0.1.schema.json" ]] && leftovers+=("schemas/agent-assurance-case-v0.1.schema.json")
  check "no v0.1 leftover files" "fail" "found: ${leftovers[*]} (delete via Finder before publishing)"
else
  check "no v0.1 leftover files" "ok"
fi

# 1b. No build caches, Python caches, or Mac zip artifacts (must not be pushed public).
junk=$(find . \( -name ".pytest_cache" -o -name "__pycache__" -o -name "pytest-cache-files-*" -o -name "__MACOSX" -o -name "*.pyc" -o -name ".DS_Store" \) -print 2>/dev/null | sort)
if [[ -n "$junk" ]]; then
  count=$(printf "%s\n" "$junk" | wc -l | tr -d ' ')
  first=$(printf "%s\n" "$junk" | head -1)
  check "no build cache or junk artifacts" "fail" "$count item(s) found; first: $first (delete via Finder before publishing)"
else
  check "no build cache or junk artifacts" "ok"
fi

# 2. Test suite passes with 10/10. Disable pytest cache + bytecode writes so the gate doesn't regenerate junk.
if PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/ --basetemp=/tmp/aac_pub_gate -p no:cacheprovider -q 2>&1 | grep -qE "^10 passed"; then
  check "pytest 10/10 passes" "ok"
else
  check "pytest 10/10 passes" "fail" "run 'python3 -m pytest tests/ -v' to see failures"
fi

# 3. Each bundled example verifies.
for ex in pass-with-coverage skill-poisoning-hold critical-exfiltration-fail; do
  out=$(PYTHONDONTWRITEBYTECODE=1 python3 verifier/verify.py "examples/${ex}.json" --allow-demo-key 2>&1 | tail -1)
  if [[ "$out" == "VERIFIED" ]]; then
    check "example ${ex}.json verifies" "ok"
  else
    check "example ${ex}.json verifies" "fail" "got: $out"
  fi
done

# 4. Bug-1 regression — invalid sig + no flags must produce NOT VERIFIED.
tmp=$(mktemp)
python3 -c "
import json, sys
with open('examples/pass-with-coverage.json') as f: case = json.load(f)
case['evidence']['signature'] = 'ed25519:' + 'A' * 88
with open('$tmp', 'w') as f: json.dump(case, f)
"
regression_out=$(PYTHONDONTWRITEBYTECODE=1 python3 verifier/verify.py "$tmp" 2>&1 | tail -1)
rm -f "$tmp"
if [[ "$regression_out" == "NOT VERIFIED" ]]; then
  check "bug-1 regression (silent sig skip caught)" "ok"
else
  check "bug-1 regression (silent sig skip caught)" "fail" "got: $regression_out"
fi

# 5. Schema URI in SPEC.md matches the schema file on disk.
if grep -q "agent-assurance-case-v0.2.schema.json" SPEC.md && [[ -f "schemas/agent-assurance-case-v0.2.schema.json" ]]; then
  check "schema URI matches shipped schema" "ok"
else
  check "schema URI matches shipped schema" "fail" "SPEC.md references a schema file not present in schemas/"
fi

# 6. Verifier source contains V7 hardening hooks.
hooks=$(grep -cE "_SUPPORTED_PROFILES|_no_duplicate_object_pairs|validate_timestamps_utc|enforce_profile|_evidence_reference_errors" verifier/verify.py 2>/dev/null || echo 0)
if [[ "$hooks" -ge 5 ]]; then
  check "V7 hardening hooks present in verifier" "ok" "$hooks references found"
else
  check "V7 hardening hooks present in verifier" "fail" "only $hooks of 5 expected hooks found"
fi

# 7. Final junk-artifact check, AFTER pytest/verifier execution, because Python can recreate caches mid-gate.
post_junk=$(find . \( -name ".pytest_cache" -o -name "__pycache__" -o -name "pytest-cache-files-*" -o -name "__MACOSX" -o -name "*.pyc" -o -name ".DS_Store" \) -print 2>/dev/null | sort)
if [[ -n "$post_junk" ]]; then
  count=$(printf "%s\n" "$post_junk" | wc -l | tr -d ' ')
  first=$(printf "%s\n" "$post_junk" | head -1)
  check "no post-test cache or junk artifacts" "fail" "$count item(s) found; first: $first (re-clean and rerun gate)"
else
  check "no post-test cache or junk artifacts" "ok"
fi

echo
printf '%s\n' "${RESULTS[@]}"
echo
echo "Summary: $PASS passed, $FAIL failed."
if [[ $FAIL -eq 0 ]]; then
  echo "AAC v0.2-candidate.2 publication gate: PASSED"
  echo "Ready to push to public repo."
  exit 0
else
  echo "AAC v0.2-candidate.2 publication gate: FAILED"
  echo "Fix the failed items before pushing public."
  exit 1
fi
