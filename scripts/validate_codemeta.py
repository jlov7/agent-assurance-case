#!/usr/bin/env python3
"""Validate AAC CodeMeta metadata against release evidence."""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parents[1]
CODEMETA_PATH = ROOT / "codemeta.json"
RELEASE_EVIDENCE_PATH = ROOT / "release-evidence.v0.2-candidate.8.json"

EXPECTED_CONTEXT = "https://w3id.org/codemeta/3.1"
EXPECTED_TYPE = "SoftwareSourceCode"
EXPECTED_ORCID = "https://orcid.org/0009-0001-6300-9155"
EXPECTED_LICENSES = {
    "https://spdx.org/licenses/Apache-2.0",
    "https://spdx.org/licenses/CC-BY-4.0",
}
REQUIRED_KEYWORDS = {
    "agentic-ai",
    "ai-assurance",
    "release-gates",
    "evidence",
    "json-schema",
    "ed25519",
    "verification",
}


def fail(message: str) -> NoReturn:
    print(f"CodeMeta metadata invalid: {message}", file=sys.stderr)
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
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=duplicate_rejecting_object)
    except json.JSONDecodeError as exc:
        fail(f"{path.name} is not valid JSON: {exc}")
    if not isinstance(value, Mapping):
        fail(f"{path.name} must be a JSON object")
    return value


def require_mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        fail(f"{field} must be an object")
    return value


def require_list(value: object, field: str) -> list[object]:
    if not isinstance(value, list):
        fail(f"{field} must be an array")
    return value


def require_equal(actual: object, expected: object, field: str) -> None:
    if actual != expected:
        fail(f"{field} must be {expected!r}, got {actual!r}")


def main() -> int:
    codemeta = load_json(CODEMETA_PATH)
    evidence = load_json(RELEASE_EVIDENCE_PATH)
    release = require_mapping(evidence.get("release"), "release evidence release")
    citation = require_mapping(evidence.get("citation"), "release evidence citation")

    release_name = release.get("name")
    release_version = release.get("version")
    release_repository = release.get("repository")
    doi_url = release.get("doi_url")

    require_equal(codemeta.get("@context"), EXPECTED_CONTEXT, "@context")
    require_equal(codemeta.get("@type"), EXPECTED_TYPE, "@type")
    require_equal(codemeta.get("name"), release_name, "name")
    require_equal(codemeta.get("version"), release_version, "version")
    require_equal(codemeta.get("identifier"), doi_url, "identifier")
    require_equal(codemeta.get("sameAs"), doi_url, "sameAs")
    require_equal(codemeta.get("url"), release_repository, "url")
    require_equal(codemeta.get("codeRepository"), release_repository, "codeRepository")
    require_equal(codemeta.get("datePublished"), str(release.get("published_at"))[:10], "datePublished")
    require_equal(codemeta.get("issueTracker"), f"{release_repository}/issues", "issueTracker")
    require_equal(codemeta.get("programmingLanguage"), "Python", "programmingLanguage")

    author = require_mapping(codemeta.get("author"), "author")
    require_equal(author.get("@type"), "Person", "author.@type")
    require_equal(author.get("@id"), citation.get("orcid"), "author.@id")
    require_equal(author.get("@id"), EXPECTED_ORCID, "author.@id")
    require_equal(author.get("givenName"), "Jason Mark", "author.givenName")
    require_equal(author.get("familyName"), "Lovell", "author.familyName")

    licenses = {str(item) for item in require_list(codemeta.get("license"), "license")}
    if licenses != EXPECTED_LICENSES:
        fail(f"license must be {sorted(EXPECTED_LICENSES)!r}, got {sorted(licenses)!r}")

    keywords = {str(item) for item in require_list(codemeta.get("keywords"), "keywords")}
    missing_keywords = sorted(REQUIRED_KEYWORDS - keywords)
    if missing_keywords:
        fail(f"keywords missing {missing_keywords!r}")

    print("CodeMeta metadata: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
