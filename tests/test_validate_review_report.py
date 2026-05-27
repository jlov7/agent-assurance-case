from __future__ import annotations

import copy
import json
from pathlib import Path

from verifier import validate_review_report


BASE = Path(__file__).resolve().parents[1]


def _valid_report() -> dict:
    report = json.loads((BASE / "review-report-template.json").read_text())
    report["reviewer"] = {
        "name": "Example Reviewer",
        "affiliation_or_project": "example-verifier",
        "contact_or_url": "https://example.com/review",
    }
    report["review"]["summary"] = "Checked AAC v0.2 vectors with an independent parser."
    report["review"]["outcome"] = "confirmation"
    report["review"]["public_artifact_url"] = "https://example.com/aac-review"
    report["implementation"] = {
        "applicable": True,
        "name": "example-aac-verifier",
        "source_url": "https://example.com/example-aac-verifier",
        "version_or_commit": "abc1234",
        "language_runtime": "Python 3.12",
        "support_scope": "aac.core verifier",
        "profiles_supported": ["aac.core"],
        "notes": "Example implementation report.",
    }
    report["reproduction"]["environment"] = "Python 3.12 on Linux"
    report["reproduction"]["commands"] = ["python3 verifier/check_vectors.py"]
    report["reproduction"]["observed_output"] = [
        "AAC vectors: canonicalization accept=6 reject=5",
        "AAC vectors: sign_verify=aac-v0.2-demo-sign-verify-pass-with-coverage",
        "AAC vectors: valid",
    ]
    report["vector_conformance"]["observed_vector_output"] = list(
        validate_review_report.EXPECTED_VECTOR_OUTPUT
    )
    report["claim_boundary"]["independent_review_claimed"] = True
    return report


def _write_report(tmp_path: Path, report: dict) -> Path:
    path = tmp_path / "review-report.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return path


def test_valid_review_report_passes(tmp_path: Path) -> None:
    assert validate_review_report.validate_review_report(
        _write_report(tmp_path, _valid_report())
    ) == []


def test_cli_accepts_valid_review_report(tmp_path: Path, capsys) -> None:
    path = _write_report(tmp_path, _valid_report())

    assert validate_review_report.main([str(path)]) == 0

    assert capsys.readouterr().out.strip() == "AAC review report: valid submission."


def test_template_is_not_a_valid_submission(tmp_path: Path) -> None:
    errors = validate_review_report.validate_review_report(
        BASE / "review-report-template.json"
    )

    assert "reviewer.name must be populated" in errors
    assert "review.summary must be populated" in errors
    assert "implementation.name must be populated" in errors


def test_independent_implementation_review_requires_implementation_metadata(
    tmp_path: Path,
) -> None:
    report = _valid_report()
    report["implementation"]["applicable"] = False
    report["implementation"]["name"] = ""
    report["implementation"]["source_url"] = ""
    report["implementation"]["version_or_commit"] = ""
    report["implementation"]["language_runtime"] = ""
    report["implementation"]["support_scope"] = "not-applicable"

    errors = validate_review_report.validate_review_report(
        _write_report(tmp_path, report)
    )

    assert (
        "implementation.applicable must be true for independent verifier or parser reviews"
        in errors
    )
    assert "implementation.name must be populated" in errors
    assert "implementation.source_url must be populated" in errors
    assert "implementation.version_or_commit must be populated" in errors
    assert "implementation.language_runtime must be populated" in errors
    assert "implementation.support_scope must describe the implementation scope" in errors


def test_profile_implementation_review_names_supported_profiles(tmp_path: Path) -> None:
    report = _valid_report()
    report["implementation"]["support_scope"] = "aac.core verifier plus profiles"
    report["implementation"]["profiles_supported"] = []

    errors = validate_review_report.validate_review_report(
        _write_report(tmp_path, report)
    )

    assert (
        "implementation.profiles_supported must name supported profiles when support_scope includes profiles"
        in errors
    )


def test_independent_review_claim_requires_public_non_sensitive_artifact(
    tmp_path: Path,
) -> None:
    report = _valid_report()
    report["review"]["public_artifact_url"] = ""
    report["review"]["security_sensitive"] = True

    errors = validate_review_report.validate_review_report(
        _write_report(tmp_path, report)
    )

    assert "review.public_artifact_url must be populated" in errors
    assert "review.security_sensitive must be false for independent review claims" in errors


def test_vector_review_requires_exact_vector_output(tmp_path: Path) -> None:
    report = _valid_report()
    report["vector_conformance"]["observed_vector_output"][2] = "AAC vectors: NOT VALID"

    errors = validate_review_report.validate_review_report(
        _write_report(tmp_path, report)
    )

    assert (
        "vector_conformance.observed_vector_output must match the AAC v0.2 vector output"
        in errors
    )


def test_confirmation_cannot_include_unresolved_findings(tmp_path: Path) -> None:
    report = _valid_report()
    report["findings"].append(
        {
            "id": "AAC-REVIEW-001",
            "severity": "medium",
            "area": "schema",
            "summary": "Example issue",
            "evidence": "Example evidence",
            "suggested_disposition": "schema-change",
        }
    )

    errors = validate_review_report.validate_review_report(
        _write_report(tmp_path, report)
    )

    assert "confirmation reports must not include unresolved findings" in errors


def test_rejects_duplicate_json_object_members(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.json"
    path.write_text(
        '{"report_type":"aac-external-review-report","report_type":"other"}',
        encoding="utf-8",
    )

    errors = validate_review_report.validate_review_report(path)

    assert errors == ["duplicate JSON object member: report_type"]


def test_rejects_duplicate_finding_ids(tmp_path: Path) -> None:
    report = _valid_report()
    report["review"]["outcome"] = "defect"
    finding = {
        "id": "AAC-REVIEW-001",
        "severity": "medium",
        "area": "schema",
        "summary": "Example issue",
        "evidence": "Example evidence",
        "suggested_disposition": "schema-change",
    }
    report["findings"] = [copy.deepcopy(finding), copy.deepcopy(finding)]

    errors = validate_review_report.validate_review_report(
        _write_report(tmp_path, report)
    )

    assert "duplicate finding id: AAC-REVIEW-001" in errors
