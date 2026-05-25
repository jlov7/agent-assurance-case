#!/usr/bin/env python3
"""Validate static and live GitHub repository posture for AAC."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
POSTURE_PATH = ROOT / "repository-posture.json"
SCHEMA_PATH = ROOT / "repository-posture.schema.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_static(posture: dict[str, Any]) -> None:
    schema = load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(posture)


def gh_token() -> str | None:
    env_token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if env_token:
        return env_token
    try:
        return subprocess.check_output(
            ["gh", "auth", "token"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None


def github_json(path: str, token: str | None) -> Any:
    request = urllib.request.Request(
        f"https://api.github.com/{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"GitHub API request failed for {path}: {exc}") from exc


def require_equal(label: str, actual: Any, expected: Any) -> None:
    if actual != expected:
        raise SystemExit(f"{label} mismatch: {actual!r} != {expected!r}")


def live_snapshot(repository: str, token: str | None) -> dict[str, Any]:
    repo = github_json(f"repos/{repository}", token)
    protection = github_json(f"repos/{repository}/branches/main/protection", token)
    alerts = github_json(f"repos/{repository}/code-scanning/alerts", token)
    open_alerts = [alert for alert in alerts if alert.get("state") == "open"]
    pr_reviews = protection.get("required_pull_request_reviews") or {}
    analysis = repo.get("security_and_analysis") or {}
    return {
        "merge_policy": {
            "allow_merge_commit": repo.get("allow_merge_commit"),
            "allow_rebase_merge": repo.get("allow_rebase_merge"),
            "allow_squash_merge": repo.get("allow_squash_merge"),
            "delete_branch_on_merge": repo.get("delete_branch_on_merge"),
        },
        "branch_protection": {
            "strict_required_checks": protection["required_status_checks"]["contexts"],
            "required_pull_request_reviews": bool(pr_reviews),
            "required_approving_review_count": pr_reviews.get(
                "required_approving_review_count"
            ),
            "enforce_admins": protection["enforce_admins"]["enabled"],
            "required_linear_history": protection["required_linear_history"]["enabled"],
            "required_conversation_resolution": protection[
                "required_conversation_resolution"
            ]["enabled"],
            "allow_force_pushes": protection["allow_force_pushes"]["enabled"],
            "allow_deletions": protection["allow_deletions"]["enabled"],
        },
        "security_analysis": {
            name: (analysis.get(name) or {}).get("status")
            for name in (
                "dependabot_security_updates",
                "secret_scanning",
                "secret_scanning_push_protection",
                "secret_scanning_non_provider_patterns",
                "secret_scanning_validity_checks",
            )
        },
        "code_scanning": {"open_alerts": len(open_alerts)},
    }


def validate_live(posture: dict[str, Any], token: str | None) -> None:
    snapshot = live_snapshot(str(posture["repository"]), token)
    for section in (
        "merge_policy",
        "security_analysis",
        "code_scanning",
    ):
        require_equal(section, snapshot[section], posture[section])
    expected_branch = posture["branch_protection"]
    actual_branch = snapshot["branch_protection"]
    for key in (
        "strict_required_checks",
        "required_pull_request_reviews",
        "required_approving_review_count",
        "enforce_admins",
        "required_linear_history",
        "required_conversation_resolution",
        "allow_force_pushes",
        "allow_deletions",
    ):
        require_equal(f"branch_protection.{key}", actual_branch[key], expected_branch[key])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--live",
        action="store_true",
        help="also compare repository-posture.json to live GitHub settings",
    )
    args = parser.parse_args()

    posture = load_json(POSTURE_PATH)
    validate_static(posture)
    if args.live:
        validate_live(posture, gh_token())
        print("Repository posture: valid static + live")
    else:
        print("Repository posture: valid static")
    return 0


if __name__ == "__main__":
    sys.exit(main())
