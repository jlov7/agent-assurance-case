#!/usr/bin/env python3
"""Validate a submitted AAC external review report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "review-report.schema.json"

PLACEHOLDER_STRINGS = {"", "n/a", "none", "todo", "tbd", "placeholder"}
VECTOR_REVIEW_TYPES = {
    "independent-verifier-or-parser",
    "canonicalization-or-signature-vectors",
}
EXPECTED_VECTOR_OUTPUT = [
    "AAC vectors: canonicalization accept=6 reject=5",
    "AAC vectors: sign_verify=aac-v0.2-demo-sign-verify-pass-with-coverage",
    "AAC vectors: valid",
]
IMPLEMENTATION_REVIEW_TYPE = "independent-verifier-or-parser"


def _no_duplicate_object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object member: {key}")
        result[key] = value
    return result


def load_json_no_duplicates(path: Path) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_no_duplicate_object_pairs,
        )
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc


def _is_placeholder(value: object) -> bool:
    return str(value).strip().lower() in PLACEHOLDER_STRINGS


def _require_populated(
    errors: list[str],
    document: dict[str, Any],
    dotted_path: str,
) -> None:
    value: Any = document
    for part in dotted_path.split("."):
        if not isinstance(value, dict):
            errors.append(f"{dotted_path} must be populated")
            return
        value = value.get(part)
    if _is_placeholder(value):
        errors.append(f"{dotted_path} must be populated")


def _duplicate_finding_errors(findings: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for finding in findings:
        finding_id = str(finding.get("id", ""))
        if finding_id in seen:
            errors.append(f"duplicate finding id: {finding_id}")
        seen.add(finding_id)
    return errors


def _implementation_metadata_errors(report: dict[str, Any], review_type: object) -> list[str]:
    errors: list[str] = []
    implementation = report.get("implementation", {})
    if not isinstance(implementation, dict):
        return errors

    if review_type == IMPLEMENTATION_REVIEW_TYPE:
        if implementation.get("applicable") is not True:
            errors.append(
                "implementation.applicable must be true for independent verifier or parser reviews"
            )
        for field in (
            "implementation.name",
            "implementation.source_url",
            "implementation.version_or_commit",
            "implementation.language_runtime",
        ):
            _require_populated(errors, report, field)
        if implementation.get("support_scope") == "not-applicable":
            errors.append("implementation.support_scope must describe the implementation scope")

    if implementation.get("support_scope") == "aac.core verifier plus profiles":
        profiles = implementation.get("profiles_supported", [])
        if not isinstance(profiles, list) or not profiles:
            errors.append(
                "implementation.profiles_supported must name supported profiles when support_scope includes profiles"
            )
        elif any(_is_placeholder(profile) for profile in profiles):
            errors.append("implementation.profiles_supported must not contain placeholders")

    return errors


def validate_review_report(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        report = load_json_no_duplicates(path)
    except ValueError as exc:
        return [str(exc)]

    if not isinstance(report, dict):
        return ["review report root must be an object"]

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    for error in sorted(validator.iter_errors(report), key=lambda item: item.path):
        location = ".".join(str(part) for part in error.path) or "<root>"
        errors.append(f"{location}: {error.message}")

    for field in (
        "reviewer.name",
        "reviewer.affiliation_or_project",
        "reviewer.contact_or_url",
        "review.summary",
        "reproduction.environment",
    ):
        _require_populated(errors, report, field)

    commands = report.get("reproduction", {}).get("commands", [])
    if isinstance(commands, list) and any(_is_placeholder(command) for command in commands):
        errors.append("reproduction.commands must not contain placeholders")

    observed_output = report.get("reproduction", {}).get("observed_output", [])
    if isinstance(observed_output, list) and any(
        _is_placeholder(output) for output in observed_output
    ):
        errors.append("reproduction.observed_output must not contain placeholders")

    review = report.get("review", {})
    review_type = review.get("review_type") if isinstance(review, dict) else None
    errors.extend(_implementation_metadata_errors(report, review_type))
    vector_conformance = report.get("vector_conformance", {})
    if isinstance(vector_conformance, dict):
        applicable = vector_conformance.get("applicable")
        method = vector_conformance.get("method")
        vector_output = vector_conformance.get("observed_vector_output", [])
        if review_type in VECTOR_REVIEW_TYPES:
            if applicable is not True:
                errors.append("vector_conformance.applicable must be true for vector reviews")
            if method == "not-applicable":
                errors.append("vector_conformance.method must describe the vector check")
            if not isinstance(vector_output, list) or vector_output != EXPECTED_VECTOR_OUTPUT:
                errors.append(
                    "vector_conformance.observed_vector_output must match the AAC v0.2 vector output"
                )

    if review.get("outcome") == "confirmation":
        findings = report.get("findings", [])
        if findings:
            errors.append("confirmation reports must not include unresolved findings")

    findings = report.get("findings", [])
    if isinstance(findings, list):
        errors.extend(
            _duplicate_finding_errors(
                [item for item in findings if isinstance(item, dict)]
            )
        )

    claim_boundary = report.get("claim_boundary", {})
    if isinstance(claim_boundary, dict):
        if claim_boundary.get("endorsement_claimed") is not False:
            errors.append("claim_boundary.endorsement_claimed must be false")
        if claim_boundary.get("legal_certification_claimed") is not False:
            errors.append("claim_boundary.legal_certification_claimed must be false")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path, help="Path to submitted review report JSON")
    args = parser.parse_args(argv)

    errors = validate_review_report(args.report)
    if errors:
        print("AAC review report: NOT VALID")
        for error in errors:
            print(f"- {error}")
        return 1

    print("AAC review report: valid submission.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
