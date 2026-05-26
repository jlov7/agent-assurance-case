#!/usr/bin/env python3
"""Validate AAC external-review status against release evidence and public docs."""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parents[1]
RELEASE_EVIDENCE_PATH = ROOT / "release-evidence.v0.2-candidate.7.json"
LEDGER_PATH = ROOT / "EXTERNAL_REVIEW_LEDGER.md"
README_PATH = ROOT / "README.md"
REVIEW_GUIDE_PATH = ROOT / "REVIEW_GUIDE.md"

EXPECTED_LEDGER = "EXTERNAL_REVIEW_LEDGER.md"
EXPECTED_PUBLIC_ISSUE = "https://github.com/jlov7/agent-assurance-case/issues/2"
EXPECTED_MATURITY = "public draft candidate"
EXPECTED_FINGERPRINT_COMMAND = "python3 scripts/verify_release_fingerprints.py"
EXPECTED_NOT_CLAIMED = {
    "legal certification",
    "employer endorsement",
    "standards-body endorsement",
    "production key governance",
    "accepted independent cryptographic review",
}


def fail(message: str) -> NoReturn:
    print(f"External review status invalid: {message}", file=sys.stderr)
    raise SystemExit(1)


def duplicate_rejecting_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    seen: set[str] = set()
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in seen:
            fail(f"duplicate JSON member {key!r}")
        seen.add(key)
        result[key] = value
    return result


def load_json(path: Path) -> Mapping[str, object]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=duplicate_rejecting_object,
        )
    except json.JSONDecodeError as exc:
        fail(f"{path.name} is not valid JSON: {exc}")
    if not isinstance(value, Mapping):
        fail(f"{path.name} must be a JSON object")
    return value


def require_mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        fail(f"{field} must be an object")
    return value


def require_equal(actual: object, expected: object, field: str) -> None:
    if actual != expected:
        fail(f"{field} must be {expected!r}, got {actual!r}")


def require_contains(text: str, needle: str, path: Path) -> None:
    if needle not in text:
        fail(f"{path.name} must contain {needle!r}")


def main() -> int:
    evidence = load_json(RELEASE_EVIDENCE_PATH)
    release_checks = require_mapping(evidence.get("release_checks"), "release_checks")
    external_review = require_mapping(evidence.get("external_review"), "external_review")
    claim_boundary = require_mapping(evidence.get("claim_boundary"), "claim_boundary")

    require_equal(external_review.get("ledger"), EXPECTED_LEDGER, "external_review.ledger")
    require_equal(
        external_review.get("public_issue"),
        EXPECTED_PUBLIC_ISSUE,
        "external_review.public_issue",
    )
    require_equal(
        external_review.get("accepted_independent_review"),
        False,
        "external_review.accepted_independent_review",
    )
    require_equal(claim_boundary.get("maturity"), EXPECTED_MATURITY, "claim_boundary.maturity")
    require_equal(
        claim_boundary.get("self_verification_evidence"),
        True,
        "claim_boundary.self_verification_evidence",
    )
    require_equal(
        claim_boundary.get("independent_validation_claimed"),
        False,
        "claim_boundary.independent_validation_claimed",
    )
    require_equal(
        release_checks.get("current_main_release_fingerprint_command"),
        EXPECTED_FINGERPRINT_COMMAND,
        "release_checks.current_main_release_fingerprint_command",
    )

    not_claimed = claim_boundary.get("not_claimed")
    if not isinstance(not_claimed, list):
        fail("claim_boundary.not_claimed must be an array")
    missing_not_claimed = sorted(EXPECTED_NOT_CLAIMED - {str(item) for item in not_claimed})
    if missing_not_claimed:
        fail(f"claim_boundary.not_claimed missing {missing_not_claimed!r}")

    ledger = LEDGER_PATH.read_text(encoding="utf-8")
    readme = README_PATH.read_text(encoding="utf-8")
    review_guide = REVIEW_GUIDE_PATH.read_text(encoding="utf-8")

    require_contains(
        ledger,
        "No independent verifier implementation, cryptographic review, schema/profile review, or deployment review has been accepted",
        LEDGER_PATH,
    )
    require_contains(ledger, "| none yet | none yet | none yet | none yet |", LEDGER_PATH)
    require_contains(ledger, "not yet independently validated", LEDGER_PATH)
    require_contains(readme, "no accepted independent review yet", README_PATH)
    require_contains(readme, EXPECTED_PUBLIC_ISSUE, README_PATH)
    require_contains(review_guide, "no recorded independent verifier implementation", REVIEW_GUIDE_PATH)
    require_contains(review_guide, EXPECTED_LEDGER, REVIEW_GUIDE_PATH)

    print("External review status: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
