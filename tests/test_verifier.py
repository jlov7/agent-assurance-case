import importlib.util
import json
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("verify", BASE / "verifier" / "verify.py")
assert spec is not None and spec.loader is not None
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)


def load(name):
    return json.loads((BASE / "examples" / name).read_text())


def resign(case):
    priv, _ = verify._demo_keypair()
    case["evidence"]["signed_by"] = verify._DEMO_SIGNED_BY
    case["evidence"]["key_id"] = verify._DEMO_KEY_ID
    verify.sign_case(case, priv)
    return case


def write(tmp_path, name, case):
    path = tmp_path / name
    path.write_text(json.dumps(case, indent=2))
    return path


def test_bad_signature_fails_without_silent_skip(tmp_path):
    case = load("pass-with-coverage.json")
    case["evidence"]["signature"] = "ed25519:" + "A" * 88
    path = write(tmp_path, "case.json", case)
    assert verify.verify(path, None, allow_demo_key=False, verbose=False) == 1


def test_demo_public_key_verifies_example():
    assert (
        verify.verify(
            BASE / "examples" / "pass-with-coverage.json",
            BASE / "keys" / "demo-issuer-v0.2.pub",
            allow_demo_key=False,
            verbose=False,
        )
        == 0
    )


def test_evidence_metadata_tamper_changes_hash(tmp_path):
    case = load("pass-with-coverage.json")
    case["evidence"]["signed_by"] = "did:web:evil.example"
    path = write(tmp_path, "case.json", case)
    assert verify.verify(path, None, allow_demo_key=True, verbose=False) == 1


def test_partial_inventory_prevents_pass(tmp_path):
    case = load("pass-with-coverage.json")
    case["coverage"]["inventory_status"] = "partial"
    resign(case)
    path = write(tmp_path, "case.json", case)
    assert verify.verify(path, None, allow_demo_key=True, verbose=False) == 1


def test_finding_references_undeclared_asset_fails(tmp_path):
    case = load("skill-poisoning-hold.json")
    case["findings"][0]["subject_asset_id"] = "skill:missing@1.0.0"
    resign(case)
    path = write(tmp_path, "case.json", case)
    assert verify.verify(path, None, allow_demo_key=True, verbose=False) == 1


def test_fail_example_verifies_as_fail():
    case = load("critical-exfiltration-fail.json")
    expected, reasons = verify.recompute_verdict(case)
    assert expected == "fail"


def test_profile_missing_required_skill_detector_fails(tmp_path):
    case = load("pass-with-coverage.json")
    for run in case["coverage"]["detector_runs"]:
        if run["detector"]["name"] == "runwright-skill-static":
            run["categories"] = [
                c for c in run["categories"] if c != "skill-secret-exposure"
            ]
    resign(case)
    path = write(tmp_path, "case.json", case)
    assert verify.verify(path, None, allow_demo_key=True, verbose=False) == 1


def test_evidence_ref_missing_from_artifact_manifest_fails(tmp_path):
    case = load("pass-with-coverage.json")
    case["findings"].append(
        {
            "finding_id": "finding_missing_ref",
            "category": "RUNWRIGHT-SKILL-INFO",
            "severity": "info",
            "status": "open",
            "subject_asset_id": case["assets"][0]["asset_id"],
            "title": "Informational finding with unbound evidence",
            "created_at": "2026-05-11T13:00:01Z",
            "evidence_refs": ["evidence://missing/not-in-manifest.json"],
        }
    )
    resign(case)
    path = write(tmp_path, "case.json", case)
    assert verify.verify(path, None, allow_demo_key=True, verbose=False) == 1


def test_release_condition_evidence_ref_missing_from_artifact_manifest_fails(tmp_path):
    case = load("pass-with-coverage.json")
    case["release_conditions"] = [
        {
            "condition_id": "cond_1",
            "status": "satisfied",
            "description": "Manual review passed",
            "evidence_ref": "evidence://missing/not-in-manifest-condition.json",
        }
    ]
    resign(case)
    path = write(tmp_path, "case.json", case)
    assert verify.verify(path, None, allow_demo_key=True, verbose=False) == 1


def test_duplicate_json_member_rejected():
    raw = '{"schema_version":"0.2","schema_version":"0.2"}'
    try:
        verify.load_json_no_duplicates(raw)
        assert False, "duplicate key should have raised"
    except ValueError as e:
        assert "Duplicate JSON object member" in str(e)


def test_non_utc_timestamp_rejected(tmp_path):
    case = load("pass-with-coverage.json")
    case["evidence"]["signed_at"] = "2026-05-11T13:00:00+00:00"
    resign(case)
    path = write(tmp_path, "case.json", case)
    assert verify.verify(path, None, allow_demo_key=True, verbose=False) == 1


def test_accepted_critical_risk_is_hold_not_pass():
    case = load("critical-exfiltration-fail.json")
    case["policy_decisions"] = []
    finding = case["findings"][0]
    finding["status"] = "accepted_risk"
    finding["resolution"] = {
        "approval_id": "approval_1",
        "expires_at": "2026-06-11T13:00:00Z",
    }
    case["approvals"] = [
        {
            "approval_id": "approval_1",
            "decision": "accept_risk",
            "decided_by": "ciso@example.com",
            "decided_at": "2026-05-11T13:10:00Z",
            "expires_at": "2026-06-11T13:00:00Z",
            "signature": "ed25519:" + "A" * 88,
        }
    ]
    expected, reasons = verify.recompute_verdict(case)
    assert expected == "hold"


def test_unsupported_profile_version_rejected(tmp_path):
    case = load("pass-with-coverage.json")
    case["profile"]["profile_version"] = "999.0.0"
    resign(case)
    path = write(tmp_path, "case.json", case)
    assert verify.verify(path, None, allow_demo_key=True, verbose=False) == 1


def test_signature_is_checked_before_profile_conformance(tmp_path, capsys):
    case = load("pass-with-coverage.json")
    case["profile"]["profile_version"] = "999.0.0"
    resign(case)
    case["evidence"]["signature"] = "ed25519:" + "A" * 88
    path = write(tmp_path, "case.json", case)

    assert (
        verify.verify(
            path,
            BASE / "keys" / "demo-issuer-v0.2.pub",
            allow_demo_key=False,
            verbose=True,
        )
        == 1
    )
    output = capsys.readouterr().out
    assert "[FAIL] signature" in output
    assert "profile conformance" not in output


def test_runwright_skill_release_requires_basic_or_higher():
    case = load("pass-with-coverage.json")
    case["profile"]["assurance_level"] = "structural"
    errors = verify.enforce_profile(case)
    assert (
        "runwright.skills.release requires aac.core assurance_level basic or higher"
        in errors
    )


def test_runwright_mcp_release_requires_basic_or_higher():
    case = load("pass-with-coverage.json")
    case["profile"] = {
        "profile_id": "runwright.mcp.release",
        "profile_version": "0.1.0",
        "assurance_level": "structural",
    }
    errors = verify.enforce_profile(case)
    assert (
        "runwright.mcp.release requires aac.core assurance_level basic or higher"
        in errors
    )


def test_aibom_artifact_must_have_aibom_role(tmp_path):
    case = load("pass-with-coverage.json")
    for artifact in case["evidence_artifacts"]:
        if artifact["uri"] == case["aibom_ref"]:
            artifact["role"] = "other"
    resign(case)
    path = write(tmp_path, "case.json", case)
    assert verify.verify(path, None, allow_demo_key=True, verbose=False) == 1


def test_skill_profile_finding_requires_evidence_refs(tmp_path):
    case = load("pass-with-coverage.json")
    case["findings"].append(
        {
            "finding_id": "finding_no_refs",
            "category": "RUNWRIGHT-SKILL-INFO",
            "severity": "info",
            "status": "open",
            "subject_asset_id": case["assets"][0]["asset_id"],
            "title": "Skill finding without evidence references",
            "created_at": "2026-05-11T13:00:01Z",
        }
    )
    resign(case)
    path = write(tmp_path, "case.json", case)
    assert verify.verify(path, None, allow_demo_key=True, verbose=False) == 1


def test_duplicate_asset_ids_rejected(tmp_path):
    case = load("pass-with-coverage.json")
    duplicate = dict(case["assets"][0])
    duplicate["name"] = "duplicate shadow asset"
    case["assets"].append(duplicate)
    resign(case)
    path = write(tmp_path, "case.json", case)
    assert verify.verify(path, None, allow_demo_key=True, verbose=False) == 1


def test_canonicalization_sorts_keys_by_utf16_code_units():
    value = {"\ue000": "bmp-private-use", "\U00010000": "supplementary"}
    assert (
        verify.canonicalize(value).decode("utf-8")
        == '{"𐀀":"supplementary","":"bmp-private-use"}'
    )


def test_canonicalization_matches_aac_supported_jcs_vectors():
    vectors = json.loads(
        (BASE / "test-vectors" / "canonicalization-v0.2.json").read_text()
    )
    for vector in vectors["accept"]:
        actual = verify.canonicalize(vector["value"])
        assert actual == vector["canonical"].encode("utf-8"), vector["name"]
        assert actual.hex() == vector["canonical_utf8_hex"], vector["name"]

    for vector in vectors["reject"]:
        try:
            verify.canonicalize(vector["value"])
            assert False, f"{vector['name']} should have raised"
        except ValueError as e:
            assert vector["error_contains"] in str(e), vector["name"]


def test_sign_verify_conformance_vector_matches_example():
    vector = json.loads((BASE / "test-vectors" / "sign-verify-v0.2.json").read_text())
    case = verify.load_json_no_duplicates((BASE / vector["case_file"]).read_text())
    vector_id = vector["vector_id"]

    canonical_hex = "".join(vector["canonical_payload_utf8_hex_chunks"])
    assert verify.payload_bytes(case).hex() == canonical_hex, vector_id
    assert verify.compute_content_hash(case) == vector["content_hash"], vector_id
    assert case["evidence"]["content_hash"] == vector["content_hash"], vector_id
    assert case["evidence"]["signature"] == vector["signature"], vector_id
    assert case["evidence"]["signature_algorithm"] == vector["signature_algorithm"], vector_id
    assert case["evidence"]["canonicalization"] == vector["canonicalization"], vector_id

    public_key = verify.load_public_key(BASE / vector["public_key_file"])
    assert verify.verify_signature(public_key, case) is True, vector_id


def test_canonicalization_rejects_unsafe_integers():
    try:
        verify.canonicalize({"n": 2**53})
        assert False, "unsafe integer should have raised"
    except ValueError as e:
        assert "safe-integer range" in str(e)


def test_canonicalization_rejects_lone_surrogates():
    for value in [{"bad": "\ud800"}, {"\udfff": "bad"}]:
        try:
            verify.canonicalize(value)
            assert False, "lone surrogate should have raised"
        except ValueError as e:
            assert "surrogate" in str(e)


def test_subject_type_skill_is_valid_for_skill_profile(tmp_path):
    case = load("pass-with-coverage.json")
    case["subject"]["subject_type"] = "skill"
    resign(case)
    path = write(tmp_path, "case.json", case)
    assert verify.verify(path, None, allow_demo_key=True, verbose=False) == 0


def test_public_cli_does_not_expose_demo_resigning():
    completed = subprocess.run(
        [sys.executable, str(BASE / "verifier" / "verify.py"), "--help"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "--resign-demo" not in completed.stdout


def test_core_profile_requires_at_least_one_asset(tmp_path):
    case = load("pass-with-coverage.json")
    case["profile"] = {
        "profile_id": "aac.core",
        "profile_version": "0.2.0",
        "assurance_level": "structural",
    }
    case["assets"] = []
    case["findings"] = []
    case["policy_decisions"] = []
    case["eval_results"] = []
    case.pop("aibom_ref", None)
    case.pop("graph_snapshot_ref", None)
    case.pop("evidence_artifacts", None)
    case["verdict"] = "pass"
    resign(case)
    path = write(tmp_path, "case.json", case)
    assert verify.verify(path, None, allow_demo_key=True, verbose=False) == 1


def _build_mcp_release_case(case):
    case["profile"] = {
        "profile_id": "runwright.mcp.release",
        "profile_version": "0.1.0",
        "assurance_level": "basic",
    }
    case["subject"]["subject_type"] = "mcp_server"
    case["assets"] = [
        {
            "asset_id": "mcp_server:internal:platform@1.0.0",
            "asset_type": "mcp_server",
            "name": "platform-mcp",
            "version": "1.0.0",
            "metadata": {"transport": "http", "auth_scheme": "oidc"},
        },
        {
            "asset_id": "mcp_tool:internal:platform.delete@1.0.0",
            "asset_type": "mcp_tool",
            "name": "platform.delete",
            "version": "1.0.0",
            "metadata": {
                "irreversible": True,
                "required_approval": "missing",
                "scopes": ["prod:delete"],
            },
        },
    ]
    case["coverage"]["detector_runs"] = [
        {
            "detector": {"name": "runwright-mcp-policy", "version": "0.2.0"},
            "scope": ["mcp_server", "mcp_tool"],
            "categories": [
                "mcp-tool-definition-risk",
                "mcp-approval-gate",
                "mcp-scope-creep",
                "mcp-tbom-presence",
            ],
            "status": "pass",
            "required": True,
            "evidence_ref": "evidence://mcp/detectors/policy.json",
        }
    ]
    case["findings"] = []
    case["eval_results"] = []
    case["policy_decisions"] = []
    case["aibom_ref"] = "evidence://mcp/aibom.cdx.json"
    case.pop("graph_snapshot_ref", None)
    case["evidence_artifacts"] = [
        {
            "artifact_id": "artifact_aibom",
            "uri": "evidence://mcp/aibom.cdx.json",
            "digest": "sha256:" + "a" * 64,
            "role": "aibom",
            "media_type": "application/vnd.cyclonedx+json",
        },
        {
            "artifact_id": "artifact_detector",
            "uri": "evidence://mcp/detectors/policy.json",
            "digest": "sha256:" + "b" * 64,
            "role": "detector_output",
            "media_type": "application/json",
        },
    ]
    case["verdict"] = "hold"
    return case


def test_mcp_profile_irreversible_tool_requires_policy_decision(tmp_path):
    case = _build_mcp_release_case(load("pass-with-coverage.json"))
    case["policy_decisions"] = []
    resign(case)
    path = write(tmp_path, "case.json", case)
    assert verify.verify(path, None, allow_demo_key=True, verbose=False) == 1


def test_mcp_profile_irreversible_tool_missing_approval_must_hold_or_deny(tmp_path):
    case = _build_mcp_release_case(load("pass-with-coverage.json"))
    case["policy_decisions"] = [
        {
            "policy_id": "runwright/mcp/require-approval-on-irreversible",
            "policy_version": "0.2.0",
            "outcome": "allow",
            "inputs_hash": "sha256:" + "0" * 64,
            "subject_asset_id": "mcp_tool:internal:platform.delete@1.0.0",
        }
    ]
    case["verdict"] = "pass"
    resign(case)
    path = write(tmp_path, "case.json", case)
    assert verify.verify(path, None, allow_demo_key=True, verbose=False) == 1


def test_mcp_profile_full_case_with_hold_policy_verifies(tmp_path):
    case = _build_mcp_release_case(load("pass-with-coverage.json"))
    case["policy_decisions"] = [
        {
            "policy_id": "runwright/mcp/require-approval-on-irreversible",
            "policy_version": "0.2.0",
            "outcome": "hold",
            "inputs_hash": "sha256:" + "0" * 64,
            "subject_asset_id": "mcp_tool:internal:platform.delete@1.0.0",
        }
    ]
    case["verdict"] = "hold"
    resign(case)
    path = write(tmp_path, "case.json", case)
    assert verify.verify(path, None, allow_demo_key=True, verbose=False) == 0


def test_policy_outcome_warn_does_not_change_verdict():
    case = load("pass-with-coverage.json")
    case["policy_decisions"].append(
        {
            "policy_id": "runwright/skills/warn-only",
            "policy_version": "0.2.0",
            "outcome": "warn",
            "inputs_hash": "sha256:" + "7" * 64,
            "subject_asset_id": case["assets"][0]["asset_id"],
        }
    )
    expected, _ = verify.recompute_verdict(case)
    assert expected == "pass"


def test_subject_type_required_by_schema(tmp_path):
    case = load("pass-with-coverage.json")
    del case["subject"]["subject_type"]
    resign(case)
    path = write(tmp_path, "case.json", case)
    assert verify.verify(path, None, allow_demo_key=True, verbose=False) == 1
