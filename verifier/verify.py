#!/usr/bin/env python3
"""
Agent Assurance Case (AAC) Reference Verifier — v0.2-candidate.6

Trust-critical properties:
- Signature verification is never silently skipped. Use --allow-demo-key for bundled examples only.
- Evidence metadata is protected: content_hash is computed over the AAC with only
  evidence.content_hash and evidence.signature nulled, not with the whole evidence object removed.
- JSON parsing rejects duplicate object names, NaN/Infinity, and the canonicalizer rejects floats.
- JSON Schema format checks are enabled and timestamps must be UTC RFC3339 strings ending in Z.
- PASS cannot be issued for unknown/partial inventory coverage or skipped/error required detectors/evals.
- Finding subject_asset_id values must point to declared assets, or the reserved literal "subject".
- Supported profiles are enforced. Unsupported profiles return NOT VERIFIED.
- Material evidence:// references must be present in evidence_artifacts for supported release profiles.
- policy_decisions[].inputs_hash values are recomputed over their canonical decision payloads.
"""

from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Tuple

try:
    from jsonschema import Draft202012Validator, FormatChecker
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey,
    )
    from cryptography.hazmat.primitives import serialization
    from cryptography.exceptions import InvalidSignature
except ImportError:
    sys.stderr.write("Missing dependency. Run: pip install -r requirements.txt\n")
    sys.exit(2)

SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent
    / "schemas"
    / "agent-assurance-case-v0.2.schema.json"
)
_DEMO_SEED = b"agent-assurance-case-v0.2-demo-keypair-seed-do-not-use-prod"
_DEMO_SIGNED_BY = "urn:agent-assurance-case:demo-issuer"
_DEMO_KEY_ID = "aac-demo-v0.2"
_JCS_MIN_SAFE_INTEGER = -(2**53) + 1
_JCS_MAX_SAFE_INTEGER = (2**53) - 1
_SUPPORTED_PROFILES = {
    "aac.core": {"0.2.0"},
    "runwright.skills.release": {"0.1.0"},
    "runwright.mcp.release": {"0.1.0"},
}
_RUNWRIGHT_RELEASE_PROFILES = {"runwright.skills.release", "runwright.mcp.release"}


def _reject_constant(value: str) -> None:
    raise ValueError(f"Non-standard JSON numeric constant rejected: {value}")


def _no_duplicate_object_pairs(pairs: list[tuple[str, Any]]) -> dict:
    obj: dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError(f"Duplicate JSON object member rejected: {key}")
        obj[key] = value
    return obj


def load_json_no_duplicates(text: str) -> Any:
    return json.loads(
        text,
        parse_constant=_reject_constant,
        object_pairs_hook=_no_duplicate_object_pairs,
    )


def _utf16_sort_key(value: str) -> bytes:
    _reject_surrogate_code_points(value)
    return value.encode("utf-16-be")


def _reject_surrogate_code_points(value: str) -> None:
    if any(0xD800 <= ord(ch) <= 0xDFFF for ch in value):
        raise ValueError(
            "AAC v0.2 reference verifier rejects lone UTF-16 surrogate code points"
        )


# Minimal deterministic canonicalizer for the constrained AAC v0.2 value domain.
# Floats are rejected to avoid an incomplete RFC 8785 number implementation.
def _jcs(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        if value < _JCS_MIN_SAFE_INTEGER or value > _JCS_MAX_SAFE_INTEGER:
            raise ValueError(
                "AAC v0.2 reference verifier rejects integers outside the JSON safe-integer range"
            )
        return str(value)
    if isinstance(value, float):
        raise ValueError(
            "AAC v0.2 reference verifier rejects floats; encode decimals as strings"
        )
    if isinstance(value, str):
        _reject_surrogate_code_points(value)
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, list):
        return "[" + ",".join(_jcs(v) for v in value) + "]"
    if isinstance(value, dict):
        # This is intentionally small and readable. Production implementations SHOULD
        # use a vetted RFC 8785/JCS library.
        return (
            "{"
            + ",".join(
                json.dumps(k, ensure_ascii=False, separators=(",", ":")) + ":" + _jcs(v)
                for k, v in sorted(value.items(), key=lambda kv: _utf16_sort_key(kv[0]))
            )
            + "}"
        )
    raise TypeError(f"Unsupported type for canonicalization: {type(value).__name__}")


def canonicalize(value: Any) -> bytes:
    return _jcs(value).encode("utf-8")


def signing_payload(case: dict) -> dict:
    payload = copy.deepcopy(case)
    payload["evidence"]["content_hash"] = None
    payload["evidence"]["signature"] = None
    return payload


def compute_content_hash(case: dict) -> str:
    digest = hashlib.sha256(canonicalize(signing_payload(case))).hexdigest()
    return f"sha256:{digest}"


def payload_bytes(case: dict) -> bytes:
    return canonicalize(signing_payload(case))


def _parse_dt(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("timestamp must be UTC RFC3339 and end with Z")
    return datetime.fromisoformat(value[:-1] + "+00:00").astimezone(timezone.utc)


def _walk_timestamps(value: Any, path: str = "") -> Iterable[tuple[str, str]]:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            if key.endswith("_at") or key in {
                "created_at",
                "expires_at",
                "occurred_at",
            }:
                if isinstance(child, str):
                    yield child_path, child
            yield from _walk_timestamps(child, child_path)
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            yield from _walk_timestamps(child, f"{path}[{idx}]")


def validate_timestamps_utc(case: dict) -> list[str]:
    errors: list[str] = []
    for path, value in _walk_timestamps(case):
        try:
            _parse_dt(value)
        except Exception as e:
            errors.append(f"{path}: {e}")
    return errors


def _is_resolution_structurally_effective(
    finding: dict, approvals_by_id: dict, signed_at: str
) -> bool:
    status = finding.get("status", "open")
    if status == "resolved":
        return True
    if status not in {"suppressed", "accepted_risk"}:
        return False
    resolution = finding.get("resolution") or {}
    approval_id = resolution.get("approval_id")
    if not approval_id:
        return False
    approval = approvals_by_id.get(approval_id)
    if not approval:
        return False
    if status == "accepted_risk" and approval.get("decision") != "accept_risk":
        return False
    if status == "suppressed" and approval.get("decision") not in {
        "approve",
        "accept_risk",
    }:
        return False
    expires_at = resolution.get("expires_at") or approval.get("expires_at")
    if expires_at:
        try:
            if _parse_dt(expires_at) <= _parse_dt(signed_at):
                return False
        except Exception:
            return False
    return True


def recompute_verdict(case: dict) -> Tuple[str, list[str]]:
    reasons: list[str] = []
    signed_at = case["evidence"]["signed_at"]
    approvals_by_id = {a.get("approval_id"): a for a in case.get("approvals", [])}
    asset_ids = {a.get("asset_id") for a in case.get("assets", [])}

    # Structural integrity conditions are FAIL because the case cannot be relied on.
    for finding in case.get("findings", []):
        subject_asset_id = finding.get("subject_asset_id")
        if subject_asset_id != "subject" and subject_asset_id not in asset_ids:
            reasons.append(
                f"Finding references undeclared asset: {finding.get('finding_id')} -> {subject_asset_id}"
            )
            return "fail", reasons

    coverage = case.get("coverage", {})
    coverage_hold = False
    if coverage.get("inventory_status") != "complete":
        reasons.append(
            f"Inventory coverage is {coverage.get('inventory_status')}, not complete"
        )
        coverage_hold = True

    for run in coverage.get("detector_runs", []):
        if run.get("required") and run.get("status") in {"skipped", "error"}:
            coverage_hold = True
            detector = run.get("detector", {}).get("name", "unknown")
            reasons.append(
                f"Required detector {detector} status is {run.get('status')}"
            )

    for condition in case.get("release_conditions", []):
        if condition.get("status") != "satisfied":
            coverage_hold = True
            reasons.append(f"Release condition open: {condition.get('condition_id')}")

    has_critical = False
    has_high_or_exception = False
    for finding in case.get("findings", []):
        severity = finding.get("severity")
        status = finding.get("status", "open")
        effective = _is_resolution_structurally_effective(
            finding, approvals_by_id, signed_at
        )
        if status == "resolved" and effective:
            continue
        if status in {"suppressed", "accepted_risk"} and effective:
            if severity in {"critical", "high"}:
                has_high_or_exception = True
                reasons.append(
                    f"{severity.upper()} finding is {status} by exception, not cleanly resolved: "
                    f"{finding.get('title')} ({finding.get('finding_id')})"
                )
            continue
        if severity == "critical":
            has_critical = True
            reasons.append(
                f"CRITICAL finding unresolved: {finding.get('title')} ({finding.get('finding_id')})"
            )
        elif severity == "high":
            has_high_or_exception = True
            reasons.append(
                f"HIGH finding unresolved: {finding.get('title')} ({finding.get('finding_id')})"
            )

    policy_hold = False
    for decision in case.get("policy_decisions", []):
        ref = f"{decision.get('policy_id')}@{decision.get('policy_version')}"
        if decision.get("outcome") == "deny":
            has_critical = True
            reasons.append(f"Policy denied: {ref}")
        elif decision.get("outcome") == "hold":
            policy_hold = True
            reasons.append(f"Policy hold: {ref}")

    eval_hold = False
    for ev in case.get("eval_results", []):
        if ev.get("required") and ev.get("status") in {"fail", "error", "skipped"}:
            eval_hold = True
            reasons.append(
                f"Required eval {ev.get('eval_id')} status is {ev.get('status')}"
            )

    if has_critical:
        return "fail", reasons
    if has_high_or_exception or policy_hold or coverage_hold or eval_hold:
        return "hold", reasons
    return "pass", reasons


def policy_inputs_hash_errors(case: dict) -> list[str]:
    errors: list[str] = []
    for idx, decision in enumerate(case.get("policy_decisions", []) or []):
        declared = decision.get("inputs_hash")
        payload = {k: v for k, v in decision.items() if k != "inputs_hash"}
        try:
            computed = "sha256:" + hashlib.sha256(canonicalize(payload)).hexdigest()
        except Exception as e:
            errors.append(f"policy_decisions[{idx}]: cannot canonicalize inputs: {e}")
            continue
        if declared != computed:
            ref = f"{decision.get('policy_id')}@{decision.get('policy_version')}"
            errors.append(
                f"policy_decisions[{idx}] {ref}: inputs_hash mismatch "
                f"declared={declared}, computed={computed}"
            )
    return errors


def _demo_keypair() -> Tuple[Ed25519PrivateKey, Ed25519PublicKey]:
    seed = hashlib.sha256(_DEMO_SEED).digest()
    priv = Ed25519PrivateKey.from_private_bytes(seed)
    return priv, priv.public_key()


def sign_case(case: dict, private_key: Ed25519PrivateKey) -> None:
    case["evidence"]["content_hash"] = None
    case["evidence"]["signature"] = None
    content_hash = compute_content_hash(case)
    sig = private_key.sign(payload_bytes(case))
    case["evidence"]["content_hash"] = content_hash
    case["evidence"]["signature"] = "ed25519:" + base64.b64encode(sig).decode("ascii")


def load_public_key(path: Path) -> Ed25519PublicKey:
    data = path.read_bytes()
    try:
        key = serialization.load_pem_public_key(data)
        if not isinstance(key, Ed25519PublicKey):
            raise TypeError("public key is not Ed25519")
        return key
    except ValueError:
        return Ed25519PublicKey.from_public_bytes(data)


def verify_signature(public_key: Ed25519PublicKey, case: dict) -> bool:
    signature = case["evidence"].get("signature")
    if not isinstance(signature, str) or not signature.startswith("ed25519:"):
        return False
    try:
        sig_bytes = base64.b64decode(signature.removeprefix("ed25519:"), validate=True)
        public_key.verify(sig_bytes, payload_bytes(case))
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False


def _required_detector_categories_present(
    case: dict, required_categories: set[str]
) -> list[str]:
    present: set[str] = set()
    skipped_or_error: set[str] = set()
    for run in case.get("coverage", {}).get("detector_runs", []):
        categories = set(run.get("categories", []) or [])
        if not run.get("required"):
            continue
        if run.get("status") in {"skipped", "error"}:
            skipped_or_error.update(categories & required_categories)
        else:
            present.update(categories & required_categories)
    missing = sorted(required_categories - present)
    bad = sorted(skipped_or_error)
    errors = []
    if missing:
        errors.append(f"missing required detector categories: {missing}")
    if bad:
        errors.append(f"required detector categories skipped/error: {bad}")
    return errors


def _evidence_uri_values(case: dict) -> set[str]:
    refs: set[str] = set()

    def add(v: Any) -> None:
        if isinstance(v, str) and v.startswith("evidence://"):
            refs.add(v)

    add(case.get("aibom_ref"))
    add(case.get("graph_snapshot_ref"))
    for run in case.get("coverage", {}).get("detector_runs", []):
        add(run.get("evidence_ref"))
    for condition in case.get("release_conditions", []) or []:
        add(condition.get("evidence_ref"))
    for tr in (
        case.get("coverage", {}).get("runtime_coverage", {}).get("trace_refs", []) or []
    ):
        add(tr)
    for finding in case.get("findings", []):
        for ref in finding.get("evidence_refs", []) or []:
            add(ref)
    for ev in case.get("eval_results", []) or []:
        add(ev.get("evidence_ref"))
    for ev in case.get("runtime_events", []) or []:
        add(ev.get("trace_ref"))
    for mapping in case.get("compliance_mappings", []) or []:
        for ref in mapping.get("evidence_refs", []) or []:
            add(ref)
    return refs


def _evidence_artifact_uris(case: dict) -> set[str]:
    uris: set[str] = set()
    for artifact in case.get("evidence_artifacts", []) or []:
        if not isinstance(artifact, dict):
            continue
        uri = artifact.get("uri")
        if isinstance(uri, str):
            uris.add(uri)
    return uris


def _evidence_artifact_roles(case: dict, uri: str) -> set[str]:
    roles: set[str] = set()
    for artifact in case.get("evidence_artifacts", []) or []:
        if not isinstance(artifact, dict) or artifact.get("uri") != uri:
            continue
        role = artifact.get("role")
        if isinstance(role, str):
            roles.add(role)
    return roles


def _evidence_reference_errors(case: dict) -> list[str]:
    refs = _evidence_uri_values(case)
    artifacts = _evidence_artifact_uris(case)
    missing = sorted(refs - artifacts)
    if missing:
        return [
            f"evidence refs missing from evidence_artifacts: {missing[:8]}"
            + (" ..." if len(missing) > 8 else "")
        ]
    return []


def _duplicate_value_errors(case: dict) -> list[str]:
    errors: list[str] = []

    def check(collection_name: str, field: str) -> None:
        seen: set[str] = set()
        duplicates: set[str] = set()
        for item in case.get(collection_name, []) or []:
            if not isinstance(item, dict):
                continue
            value = item.get(field)
            if not isinstance(value, str):
                continue
            if value in seen:
                duplicates.add(value)
            seen.add(value)
        if duplicates:
            errors.append(
                f"duplicate {collection_name}.{field} values: {sorted(duplicates)}"
            )

    check("assets", "asset_id")
    check("findings", "finding_id")
    check("approvals", "approval_id")
    check("evidence_artifacts", "artifact_id")
    check("evidence_artifacts", "uri")
    return errors


def _subject_reference_errors(case: dict) -> list[str]:
    asset_ids = {a.get("asset_id") for a in case.get("assets", []) or []}
    valid_refs = asset_ids | {"subject"}
    errors: list[str] = []
    for decision in case.get("policy_decisions", []) or []:
        subject_asset_id = decision.get("subject_asset_id")
        if subject_asset_id and subject_asset_id not in valid_refs:
            errors.append(
                f"policy decision references undeclared asset: {decision.get('policy_id')} -> {subject_asset_id}"
            )
    for event in case.get("runtime_events", []) or []:
        subject_asset_id = event.get("subject_asset_id")
        if subject_asset_id and subject_asset_id not in valid_refs:
            errors.append(
                f"runtime event references undeclared asset: {event.get('event_id')} -> {subject_asset_id}"
            )
    return errors


def _finding_evidence_ref_errors(case: dict, predicate, label: str) -> list[str]:
    errors: list[str] = []
    for finding in case.get("findings", []) or []:
        if not predicate(finding):
            continue
        refs = [
            r
            for r in finding.get("evidence_refs", []) or []
            if isinstance(r, str) and r.startswith("evidence://")
        ]
        if not refs:
            errors.append(
                f"{label} finding lacks evidence:// evidence_refs: {finding.get('finding_id')}"
            )
    return errors


def _runtime_status(case: dict) -> str:
    return case.get("coverage", {}).get("runtime_coverage", {}).get("status", "none")


def enforce_profile(case: dict) -> list[str]:
    errors: list[str] = []
    profile = case.get("profile", {})
    profile_id = profile.get("profile_id")
    profile_version = profile.get("profile_version")
    assurance = profile.get("assurance_level") or "structural"
    if profile_id not in _SUPPORTED_PROFILES:
        return [f"unsupported profile: {profile_id}"]
    if profile_version not in _SUPPORTED_PROFILES[profile_id]:
        return [f"unsupported profile version: {profile_id}@{profile_version}"]
    if profile_id in _RUNWRIGHT_RELEASE_PROFILES and assurance not in {
        "basic",
        "standard",
        "strict",
    }:
        errors.append(f"{profile_id} requires aac.core assurance_level basic or higher")

    # Core requirements for all profiles.
    errors += _duplicate_value_errors(case)
    errors += _subject_reference_errors(case)
    if not case.get("subject", {}).get("subject_type"):
        errors.append("subject.subject_type is required by aac.core")
    if not case.get("assets"):
        errors.append("aac.core requires at least one declared asset")
    if case.get("evidence", {}).get("signature_algorithm") != "Ed25519-JCS-SHA256-v1":
        errors.append("evidence.signature_algorithm must be Ed25519-JCS-SHA256-v1")
    if case.get("evidence", {}).get("canonicalization") != "RFC8785-JCS":
        errors.append("evidence.canonicalization must be RFC8785-JCS")

    if assurance in {"basic", "standard", "strict"}:
        if case.get("coverage", {}).get("inventory_status") != "complete":
            errors.append("basic+ assurance requires complete inventory")
        required_runs = [
            r
            for r in case.get("coverage", {}).get("detector_runs", [])
            if r.get("required")
        ]
        if not required_runs:
            errors.append(
                "basic+ assurance requires at least one required detector run"
            )
    if assurance in {"standard", "strict"}:
        if not case.get("aibom_ref"):
            errors.append("standard+ assurance requires aibom_ref")
        if _runtime_status(case) not in {"summary", "full"}:
            errors.append(
                "standard+ assurance requires runtime coverage summary or full"
            )
        if not case.get("compliance_mappings"):
            errors.append(
                "standard+ assurance requires at least one compliance mapping"
            )
    if assurance == "strict":
        if _runtime_status(case) != "full":
            errors.append("strict assurance requires full runtime coverage")
        approvals = {a.get("approval_id"): a for a in case.get("approvals", [])}
        for finding in case.get("findings", []) or []:
            if finding.get("status") in {"suppressed", "accepted_risk"}:
                approval_id = (finding.get("resolution") or {}).get("approval_id")
                approval = approvals.get(approval_id)
                if not approval or not approval.get("signature"):
                    errors.append(
                        f"strict assurance requires signed approval for {finding.get('finding_id')}"
                    )

    asset_types = [a.get("asset_type") for a in case.get("assets", []) or []]
    assets_by_id = {a.get("asset_id"): a for a in case.get("assets", []) or []}

    if profile_id == "runwright.skills.release":
        if not any(t in {"skill", "skill_bundle"} for t in asset_types):
            errors.append(
                "runwright.skills.release requires at least one skill or skill_bundle asset"
            )
        for asset in case.get("assets", []) or []:
            if asset.get("asset_type") in {"skill", "skill_bundle"} and not asset.get(
                "digest"
            ):
                errors.append(f"skill asset lacks digest: {asset.get('asset_id')}")
        errors += _required_detector_categories_present(
            case,
            {
                "skill-manifest-integrity",
                "skill-secret-exposure",
                "skill-executable-surface",
                "skill-tool-scope",
            },
        )
        if not case.get("aibom_ref"):
            errors.append("runwright.skills.release requires aibom_ref")
        elif "aibom" not in _evidence_artifact_roles(case, case["aibom_ref"]):
            errors.append(
                "runwright.skills.release requires aibom_ref artifact role aibom"
            )
        skill_categories = {
            "skill-manifest-integrity",
            "skill-secret-exposure",
            "skill-executable-surface",
            "skill-tool-scope",
        }
        errors += _finding_evidence_ref_errors(
            case,
            lambda finding: (
                "SKILL" in str(finding.get("category", "")).upper()
                or str(finding.get("category", "")).lower() in skill_categories
            ),
            "skill-profile",
        )
        errors += _evidence_reference_errors(case)

    if profile_id == "runwright.mcp.release":
        if not any(t in {"mcp_server", "mcp_tool"} for t in asset_types):
            errors.append(
                "runwright.mcp.release requires at least one mcp_server or mcp_tool asset"
            )
        errors += _required_detector_categories_present(
            case,
            {
                "mcp-tool-definition-risk",
                "mcp-approval-gate",
                "mcp-scope-creep",
                "mcp-tbom-presence",
            },
        )
        if not case.get("aibom_ref"):
            errors.append("runwright.mcp.release requires aibom_ref")
        elif "aibom" not in _evidence_artifact_roles(case, case["aibom_ref"]):
            errors.append(
                "runwright.mcp.release requires aibom_ref artifact role aibom"
            )
        policy_subjects = {
            d.get("subject_asset_id") for d in case.get("policy_decisions", []) or []
        }
        for asset_id, asset in assets_by_id.items():
            if (
                asset.get("asset_type") == "mcp_tool"
                and (asset.get("metadata") or {}).get("irreversible") is True
            ):
                if asset_id not in policy_subjects:
                    errors.append(
                        f"irreversible MCP tool lacks asset-linked policy decision: {asset_id}"
                    )
                else:
                    matching = [
                        d
                        for d in case.get("policy_decisions", []) or []
                        if d.get("subject_asset_id") == asset_id
                    ]
                    if (asset.get("metadata") or {}).get(
                        "required_approval"
                    ) == "missing" and not any(
                        d.get("outcome") in {"hold", "deny"} for d in matching
                    ):
                        errors.append(
                            f"irreversible MCP tool missing approval must have hold/deny policy decision: {asset_id}"
                        )
        errors += _finding_evidence_ref_errors(
            case,
            lambda finding: (
                str(finding.get("category", "")).upper().startswith("MCP")
                or (
                    assets_by_id.get(finding.get("subject_asset_id"), {}).get(
                        "asset_type"
                    )
                    in {"mcp_server", "mcp_tool"}
                )
            ),
            "mcp-profile",
        )
        errors += _evidence_reference_errors(case)

    return errors


class VerifyResult:
    def __init__(self) -> None:
        self.checks: list[Tuple[str, bool, str]] = []

    def add(self, name: str, ok: bool, detail: str = "") -> None:
        self.checks.append((name, ok, detail))

    @property
    def ok(self) -> bool:
        return all(ok for _, ok, _ in self.checks)

    def print(self, verbose: bool = False) -> None:
        for name, ok, detail in self.checks:
            mark = "OK  " if ok else "FAIL"
            line = f"  [{mark}] {name}"
            if detail and (verbose or not ok):
                line += f" — {detail}"
            print(line)
        print()
        print("VERIFIED" if self.ok else "NOT VERIFIED")


def verify(
    case_path: Path, public_key_path: Path | None, allow_demo_key: bool, verbose: bool
) -> int:
    result = VerifyResult()
    try:
        raw = case_path.read_text(encoding="utf-8")
        case = load_json_no_duplicates(raw)
    except Exception as e:
        print(f"FAIL: cannot parse JSON: {e}")
        return 2

    try:
        schema = load_json_no_duplicates(SCHEMA_PATH.read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        errors = sorted(
            validator.iter_errors(case), key=lambda e: list(e.absolute_path)
        )
        if errors:
            joined = "; ".join(
                f"{list(e.absolute_path) or '<root>'}: {e.message}" for e in errors[:8]
            )
            result.add("schema validation", False, joined)
            result.print(verbose)
            return 1
        result.add("schema validation", True)
    except Exception as e:
        result.add("schema validation", False, str(e))
        result.print(verbose)
        return 2

    ts_errors = validate_timestamps_utc(case)
    result.add("timestamp UTC validation", not ts_errors, "; ".join(ts_errors[:5]))
    if ts_errors:
        result.print(verbose)
        return 1

    try:
        expected_hash = compute_content_hash(case)
    except Exception as e:
        result.add("content hash", False, str(e))
        result.print(verbose)
        return 1

    declared_hash = case["evidence"]["content_hash"]
    if expected_hash != declared_hash:
        result.add(
            "content hash", False, f"declared={declared_hash}, computed={expected_hash}"
        )
        result.print(verbose)
        return 1
    result.add("content hash", True, expected_hash if verbose else "")

    if public_key_path:
        try:
            pub = load_public_key(public_key_path)
        except Exception as e:
            result.add("public key load", False, str(e))
            result.print(verbose)
            return 2
        ok = verify_signature(pub, case)
        result.add("signature", ok, case["evidence"].get("signed_by", ""))
        if not ok:
            result.print(verbose)
            return 1
    elif allow_demo_key:
        if (
            case["evidence"].get("signed_by") != _DEMO_SIGNED_BY
            or case["evidence"].get("key_id") != _DEMO_KEY_ID
        ):
            result.add(
                "signature (demo key)",
                False,
                "demo key allowed only for bundled demo issuer/key_id",
            )
            result.print(verbose)
            return 1
        _, pub = _demo_keypair()
        ok = verify_signature(pub, case)
        result.add(
            "signature (demo key)", ok, "DO NOT USE --allow-demo-key FOR PRODUCTION"
        )
        if not ok:
            result.print(verbose)
            return 1
    else:
        result.add(
            "signature",
            False,
            "no --public-key supplied; use --allow-demo-key only for bundled examples",
        )
        result.print(verbose)
        return 1

    profile_errors = enforce_profile(case)
    result.add("profile conformance", not profile_errors, "; ".join(profile_errors[:8]))
    if profile_errors:
        result.print(verbose)
        return 1

    policy_hash_errors = policy_inputs_hash_errors(case)
    result.add(
        "policy inputs hash",
        not policy_hash_errors,
        "; ".join(policy_hash_errors[:5]),
    )
    if policy_hash_errors:
        result.print(verbose)
        return 1

    expected_verdict, reasons = recompute_verdict(case)
    if expected_verdict != case["verdict"]:
        result.add(
            "verdict recomputation",
            False,
            f"declared={case['verdict']}, recomputed={expected_verdict}; reasons={reasons}",
        )
        result.print(verbose)
        return 1
    result.add(
        "verdict recomputation", True, f"verdict={expected_verdict}" if verbose else ""
    )

    result.print(verbose)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Agent Assurance Case v0.2-candidate.6 reference verifier"
    )
    parser.add_argument("case", type=Path)
    parser.add_argument("--public-key", type=Path, default=None)
    parser.add_argument(
        "--allow-demo-key",
        action="store_true",
        help="Use the bundled demo key for examples only",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()
    return verify(args.case, args.public_key, args.allow_demo_key, args.verbose)


if __name__ == "__main__":
    sys.exit(main())
