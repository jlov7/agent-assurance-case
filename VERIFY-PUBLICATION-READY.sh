#!/usr/bin/env bash
# Publication-readiness gate for the Agent Assurance Case (AAC) v0.2-candidate.7 artifact.
#
# Run this before pushing to the public GitHub repo. The gate checks:
#   1. The v0.1 leftover files are not present (they would weaken the public artifact).
#   2. The test suite passes.
#   3. Each of the three bundled examples verifies cleanly.
#   4. The bug-1 regression (silent signature skip) is still caught.
#   5. The schema URI in SPEC.md matches the schema file shipped.
#   6. The published demo public key verifies the examples.
#   7. The verifier source contains the trust hardening hooks.
#   8. Candidate version metadata stays synchronized across public artifacts.
#   9. REUSE/SPDX licensing metadata covers every tracked file.
#   10. Python dependency and static security checks pass.
#   11. Runtime dependency SBOM validates against verifier requirements.
#   12. Runtime dependency lock matches verifier requirements and audits cleanly.
#   13. Security Insights metadata validates against the pinned OpenSSF schema.
#   14. Repository posture metadata validates; local release runs compare live GitHub settings.
#   15. CodeMeta metadata validates against release evidence.
#   16. Citation metadata validates against release evidence and CodeMeta.
#   17. External-review status validates against release evidence and public docs.
#   18. Release asset builder dry-runs and passes shellcheck.
#
# Exit code 0 = ready to publish. Non-zero = stop and fix the listed item.

set -uo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR" || exit 2

PASS=0
FAIL=0
RESULTS=()
PYTHON_BIN="${PYTHON:-python3}"
TEMP_ROOT=""
TMP_CASE=""
PYTHONPYCACHEPREFIX="${PYTHONPYCACHEPREFIX:-/tmp/aac_pub_gate_pycache}"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPYCACHEPREFIX
# Keep Hypothesis' example database out of the repository tree so the gate's own
# pytest run cannot leave a .hypothesis/ directory behind.
HYPOTHESIS_STORAGE_DIRECTORY="${HYPOTHESIS_STORAGE_DIRECTORY:-/tmp/aac_pub_gate_hypothesis}"
export HYPOTHESIS_STORAGE_DIRECTORY
EXPECTED_CANDIDATE="v0.2-candidate.7"
EXPECTED_VERSION="${EXPECTED_CANDIDATE#v}"
EXPECTED_SCHEMA_URI="https://raw.githubusercontent.com/jlov7/agent-assurance-case/${EXPECTED_CANDIDATE}/schemas/agent-assurance-case-v0.2.schema.json"

# shellcheck disable=SC2329
cleanup() {
  if [[ -n "$TMP_CASE" && -f "$TMP_CASE" ]]; then
    rm -f "$TMP_CASE"
  fi
  if [[ -n "$TEMP_ROOT" && -d "$TEMP_ROOT" ]]; then
    rm -rf "$TEMP_ROOT"
  fi
}
trap cleanup EXIT

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

# Use a temporary venv outside the repository unless the caller explicitly supplies PYTHON.
# This keeps the publication gate reproducible from a fresh clone without generating local caches.
if [[ -z "${PYTHON:-}" ]]; then
  TEMP_ROOT=$(mktemp -d /tmp/aac_pub_gate_env.XXXXXX)
  if python3 -m venv "$TEMP_ROOT/venv" \
    && PIP_NO_CACHE_DIR=1 "$TEMP_ROOT/venv/bin/python" -m pip install --upgrade pip >/dev/null \
    && PIP_NO_CACHE_DIR=1 "$TEMP_ROOT/venv/bin/python" -m pip install -r verifier/requirements.txt -r verifier/requirements-dev.txt >/dev/null; then
    PYTHON_BIN="$TEMP_ROOT/venv/bin/python"
    check "isolated Python environment" "ok" "$PYTHON_BIN"
  else
    check "isolated Python environment" "fail" "could not create temp venv or install verifier dependencies"
  fi
else
  check "Python environment" "ok" "$PYTHON_BIN"
fi

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
junk=$(find . \( -name ".pytest_cache" -o -name ".ruff_cache" -o -name ".hypothesis" -o -name "__pycache__" -o -name "pytest-cache-files-*" -o -name "__MACOSX" -o -name "*.pyc" -o -name ".DS_Store" \) -print 2>/dev/null | sort)
if [[ -n "$junk" ]]; then
  count=$(printf "%s\n" "$junk" | wc -l | tr -d ' ')
  first=$(printf "%s\n" "$junk" | head -1)
  check "no build cache or junk artifacts" "fail" "$count item(s) found; first: $first (delete via Finder before publishing)"
else
  check "no build cache or junk artifacts" "ok"
fi

# 2. Test suite passes. Disable pytest cache + bytecode writes so the gate doesn't regenerate junk.
pytest_out=$(PYTHONDONTWRITEBYTECODE=1 "$PYTHON_BIN" -m pytest tests/ --basetemp=/tmp/aac_pub_gate -p no:cacheprovider -q 2>&1)
if printf "%s\n" "$pytest_out" | grep -qE "^[0-9]+ passed"; then
  passed=$(printf "%s\n" "$pytest_out" | sed -nE 's/^([0-9]+ passed).*/\1/p' | head -1)
  check "pytest suite passes" "ok" "$passed"
else
  check "pytest suite passes" "fail" "run 'python3 -m pytest tests/ -v' to see failures"
fi

# 3. Each bundled example verifies.
for ex in pass-with-coverage skill-poisoning-hold critical-exfiltration-fail; do
  out=$(PYTHONDONTWRITEBYTECODE=1 "$PYTHON_BIN" verifier/verify.py "examples/${ex}.json" --allow-demo-key 2>&1 | tail -1)
  if [[ "$out" == "VERIFIED" ]]; then
    check "example ${ex}.json verifies" "ok"
  else
    check "example ${ex}.json verifies" "fail" "got: $out"
  fi
done

# 3b. The published demo key must also verify the bundled examples.
for ex in pass-with-coverage skill-poisoning-hold critical-exfiltration-fail; do
  out=$(PYTHONDONTWRITEBYTECODE=1 "$PYTHON_BIN" verifier/verify.py "examples/${ex}.json" --public-key keys/demo-issuer-v0.2.pub 2>&1 | tail -1)
  if [[ "$out" == "VERIFIED" ]]; then
    check "example ${ex}.json verifies with published demo key" "ok"
  else
    check "example ${ex}.json verifies with published demo key" "fail" "got: $out"
  fi
done

# 4. Bug-1 regression — invalid sig + no flags must produce NOT VERIFIED.
TMP_CASE=$(mktemp)
"$PYTHON_BIN" -c "
import json, sys
with open('examples/pass-with-coverage.json') as f: case = json.load(f)
case['evidence']['signature'] = 'ed25519:' + 'A' * 88
with open('$TMP_CASE', 'w') as f: json.dump(case, f)
"
regression_out=$(PYTHONDONTWRITEBYTECODE=1 "$PYTHON_BIN" verifier/verify.py "$TMP_CASE" 2>&1 | tail -1)
rm -f "$TMP_CASE"
TMP_CASE=""
if [[ "$regression_out" == "NOT VERIFIED" ]]; then
  check "bug-1 regression (silent sig skip caught)" "ok"
else
  check "bug-1 regression (silent sig skip caught)" "fail" "got: $regression_out"
fi

# 5. Schema URI in SPEC.md matches the schema file on disk.
if grep -q "$EXPECTED_SCHEMA_URI" SPEC.md \
  && grep -q "\"\$id\": \"$EXPECTED_SCHEMA_URI\"" schemas/agent-assurance-case-v0.2.schema.json \
  && [[ -f "schemas/agent-assurance-case-v0.2.schema.json" ]]; then
  check "schema URI matches shipped schema" "ok"
else
  check "schema URI matches shipped schema" "fail" "SPEC.md and schema \$id must both use $EXPECTED_SCHEMA_URI"
fi

# 6. Candidate version metadata stays synchronized across public artifacts.
version_mismatches=()
grep -Fq "Current draft: \`$EXPECTED_CANDIDATE\`." README.md || version_mismatches+=("README.md")
grep -Fq "**Version:** $EXPECTED_VERSION (Draft)" SPEC.md || version_mismatches+=("SPEC.md")
grep -Fq "version: \"$EXPECTED_VERSION\"" CITATION.cff || version_mismatches+=("CITATION.cff")
grep -Fq "Reference Verifier — $EXPECTED_CANDIDATE" verifier/verify.py || version_mismatches+=("verifier/verify.py")
while IFS= read -r path; do
  [[ -n "$path" ]] && version_mismatches+=("$path")
done < <(grep -L "$EXPECTED_CANDIDATE/keys/demo-issuer-v0.2.pub" examples/*.json || true)
if [[ ! -f "THREAT_MODEL.md" ]]; then
  version_mismatches+=("THREAT_MODEL.md")
fi
if [[ ${#version_mismatches[@]} -eq 0 ]]; then
  check "candidate version metadata synchronized" "ok" "$EXPECTED_CANDIDATE"
else
  check "candidate version metadata synchronized" "fail" "mismatch: ${version_mismatches[*]}"
fi

# 7. Verifier source contains trust hardening hooks.
hooks=$(grep -cE "_SUPPORTED_PROFILES|_no_duplicate_object_pairs|validate_timestamps_utc|enforce_profile|_evidence_reference_errors" verifier/verify.py 2>/dev/null || echo 0)
if [[ "$hooks" -ge 5 ]]; then
  check "trust hardening hooks present in verifier" "ok" "$hooks references found"
else
  check "trust hardening hooks present in verifier" "fail" "only $hooks of 5 expected hooks found"
fi

# 8. Every tracked file must have machine-readable licensing metadata.
if reuse_out=$(uvx reuse lint 2>&1); then
  covered=$(printf "%s\n" "$reuse_out" | sed -nE 's#^\* Files with license information: ([0-9]+ / [0-9]+)$#\1#p' | head -1)
  check "REUSE licensing metadata" "ok" "${covered:-all tracked files covered}"
else
  check "REUSE licensing metadata" "fail" "run 'uvx reuse lint' for details"
fi

# 9. Python dependency and static security checks must pass.
if pip_audit_out=$(uv run --with-requirements verifier/requirements-dev.txt --with pip-audit pip-audit 2>&1); then
  check "Python dependency audit" "ok"
else
  check "Python dependency audit" "fail" "$(printf "%s\n" "$pip_audit_out" | tail -n 1)"
fi

if bandit_out=$(uvx bandit -q -r verifier scripts fuzz -x tests -s B404,B603,B607 2>&1); then
  check "Bandit static security scan" "ok"
else
  check "Bandit static security scan" "fail" "$(printf "%s\n" "$bandit_out" | tail -n 1)"
fi

if sbom_out=$("$PYTHON_BIN" scripts/validate_dependency_sbom.py 2>&1); then
  check "runtime dependency SBOM" "ok"
else
  check "runtime dependency SBOM" "fail" "$(printf "%s\n" "$sbom_out" | tail -n 1)"
fi

if lock_out=$(scripts/validate_dependency_lock.sh 2>&1); then
  check "runtime dependency lock" "ok"
else
  check "runtime dependency lock" "fail" "$(printf "%s\n" "$lock_out" | tail -n 1)"
fi

# 10. Security Insights metadata must remain machine-validated.
if security_insights_out=$(scripts/validate_security_insights.sh 2>&1); then
  check "Security Insights metadata" "ok"
else
  check "Security Insights metadata" "fail" "$(printf "%s\n" "$security_insights_out" | tail -n 1)"
fi

# 11. Repository posture metadata must remain machine-validated.
repository_posture_args=()
repository_posture_detail="static"
if [[ "${CI:-}" != "true" || "${REQUIRE_LIVE_REPOSITORY_POSTURE:-}" == "1" ]]; then
  repository_posture_args=(--live)
  repository_posture_detail="static + live"
fi
if [[ ${#repository_posture_args[@]} -gt 0 ]]; then
  repository_posture_out=$("$PYTHON_BIN" scripts/verify_repository_posture.py "${repository_posture_args[@]}" 2>&1)
else
  repository_posture_out=$("$PYTHON_BIN" scripts/verify_repository_posture.py 2>&1)
fi
repository_posture_rc=$?
if [[ $repository_posture_rc -eq 0 ]]; then
  if [[ "$repository_posture_detail" == "static" ]]; then
    repository_posture_detail="static; set REQUIRE_LIVE_REPOSITORY_POSTURE=1 with a token that can read branch protection to require live comparison"
  fi
  check "repository posture metadata" "ok" "$repository_posture_detail"
else
  check "repository posture metadata" "fail" "$(printf "%s\n" "$repository_posture_out" | tail -n 1)"
fi

# 12. CodeMeta discovery metadata must remain synchronized with release evidence.
if codemeta_out=$("$PYTHON_BIN" scripts/validate_codemeta.py 2>&1); then
  check "CodeMeta metadata" "ok"
else
  check "CodeMeta metadata" "fail" "$(printf "%s\n" "$codemeta_out" | tail -n 1)"
fi

# 13. Citation metadata must remain synchronized with release evidence and CodeMeta.
if citation_out=$("$PYTHON_BIN" scripts/validate_citation.py 2>&1); then
  check "citation metadata consistency" "ok"
else
  check "citation metadata consistency" "fail" "$(printf "%s\n" "$citation_out" | tail -n 1)"
fi

# 14. External review status must stay synchronized with public claim boundaries.
if external_review_out=$("$PYTHON_BIN" scripts/validate_external_review_status.py 2>&1); then
  check "external review status" "ok"
else
  check "external review status" "fail" "$(printf "%s\n" "$external_review_out" | tail -n 1)"
fi

# 15. Release asset builder must execute cleanly against the current tree.
if release_asset_out=$(scripts/build_release_assets.sh "$EXPECTED_CANDIDATE" "$TEMP_ROOT/release-assets" 2>&1); then
  check "release asset builder dry-run" "ok"
else
  check "release asset builder dry-run" "fail" "$(printf "%s\n" "$release_asset_out" | tail -n 1)"
fi

# 16. Release scripts must be shellcheck-clean.
if shellcheck_out=$(uvx --from shellcheck-py shellcheck VERIFY-PUBLICATION-READY.sh .clusterfuzzlite/build.sh scripts/build_release_assets.sh scripts/validate_dependency_lock.sh scripts/regenerate_dependency_lock.sh scripts/validate_security_insights.sh 2>&1); then
  check "shellcheck" "ok"
else
  check "shellcheck" "fail" "$(printf "%s\n" "$shellcheck_out" | tail -n 1)"
fi

# 17. Final junk-artifact check, AFTER pytest/verifier execution, because Python can recreate caches mid-gate.
post_junk=$(find . \( -path ./dist -prune \) -o \( -name ".pytest_cache" -o -name ".ruff_cache" -o -name ".hypothesis" -o -name "__pycache__" -o -name "pytest-cache-files-*" -o -name "__MACOSX" -o -name "*.pyc" -o -name ".DS_Store" \) -print 2>/dev/null | sort)
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
  echo "AAC $EXPECTED_CANDIDATE publication gate: PASSED"
  echo "Ready for final publication approval."
  exit 0
else
  echo "AAC $EXPECTED_CANDIDATE publication gate: FAILED"
  echo "Fix the failed items before pushing public."
  exit 1
fi
