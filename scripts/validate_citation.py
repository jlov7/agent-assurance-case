#!/usr/bin/env python3
"""Validate AAC citation metadata against release evidence and CodeMeta."""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parents[1]
CITATION_PATH = ROOT / "CITATION.cff"
CODEMETA_PATH = ROOT / "codemeta.json"
RELEASE_EVIDENCE_PATH = ROOT / "release-evidence.v0.2-candidate.8.json"

EXPECTED_CFF_VERSION = "1.2.0"
EXPECTED_TYPE = "software"
EXPECTED_ORCID = "https://orcid.org/0009-0001-6300-9155"
EXPECTED_FAMILY_NAME = "Lovell"
EXPECTED_GIVEN_NAME = "Jason Mark"


def fail(message: str) -> NoReturn:
    print(f"Citation metadata invalid: {message}", file=sys.stderr)
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


def strip_cff_scalar(raw_value: str) -> str:
    value = raw_value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def parse_scalar_line(line: str) -> tuple[str, str] | None:
    if ":" not in line:
        return None
    key, value = line.split(":", 1)
    key = key.strip()
    if not key:
        return None
    return key, strip_cff_scalar(value)


def top_level_scalars(lines: Sequence[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in lines:
        if not line or line[0].isspace() or line.startswith("-"):
            continue
        parsed = parse_scalar_line(line)
        if parsed is None:
            continue
        key, value = parsed
        if value:
            result[key] = value
    return result


def section_lines(lines: Sequence[str], section: str) -> list[str]:
    marker = f"{section}:"
    start: int | None = None
    for index, line in enumerate(lines):
        if line == marker:
            start = index + 1
            break
    if start is None:
        fail(f"CITATION.cff missing {section}")

    result: list[str] = []
    for line in lines[start:]:
        if line and not line[0].isspace() and not line.startswith("-"):
            break
        result.append(line)
    return result


def first_list_item_fields(lines: Sequence[str], section: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    in_first_item = False
    for line in section_lines(lines, section):
        if line.startswith("  - "):
            if in_first_item:
                break
            in_first_item = True
            parsed = parse_scalar_line(line[4:])
            if parsed is not None:
                fields[parsed[0]] = parsed[1]
            continue
        if in_first_item and line.startswith("    "):
            parsed = parse_scalar_line(line[4:])
            if parsed is not None:
                fields[parsed[0]] = parsed[1]
    if not fields:
        fail(f"CITATION.cff missing first {section} item")
    return fields


def preferred_citation_scalars(lines: Sequence[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in section_lines(lines, "preferred-citation"):
        if line.startswith("  ") and not line.startswith("    ") and not line.startswith("  - "):
            parsed = parse_scalar_line(line[2:])
            if parsed is not None and parsed[1]:
                result[parsed[0]] = parsed[1]
    return result


def require_equal(actual: object, expected: object, field: str) -> None:
    if actual != expected:
        fail(f"{field} must be {expected!r}, got {actual!r}")


def main() -> int:
    citation_lines = CITATION_PATH.read_text(encoding="utf-8").splitlines()
    cff = top_level_scalars(citation_lines)
    author = first_list_item_fields(citation_lines, "authors")
    preferred = preferred_citation_scalars(citation_lines)
    evidence = load_json(RELEASE_EVIDENCE_PATH)
    codemeta = load_json(CODEMETA_PATH)

    release = require_mapping(evidence.get("release"), "release evidence release")
    citation = require_mapping(evidence.get("citation"), "release evidence citation")
    codemeta_author = require_mapping(codemeta.get("author"), "CodeMeta author")

    release_name = release.get("name")
    release_version = release.get("version")
    release_doi = release.get("doi")
    release_doi_url = release.get("doi_url")
    release_repository = release.get("repository")
    release_date = str(release.get("published_at"))[:10]

    require_equal(cff.get("cff-version"), EXPECTED_CFF_VERSION, "cff-version")
    require_equal(cff.get("type"), EXPECTED_TYPE, "type")
    require_equal(cff.get("title"), release_name, "title")
    require_equal(cff.get("version"), release_version, "version")
    require_equal(cff.get("date-released"), release_date, "date-released")
    require_equal(cff.get("doi"), release_doi, "doi")
    require_equal(cff.get("repository-code"), release_repository, "repository-code")
    require_equal(cff.get("url"), release_repository, "url")

    require_equal(author.get("family-names"), EXPECTED_FAMILY_NAME, "authors[0].family-names")
    require_equal(author.get("given-names"), EXPECTED_GIVEN_NAME, "authors[0].given-names")
    require_equal(author.get("orcid"), citation.get("orcid"), "authors[0].orcid")
    require_equal(author.get("orcid"), EXPECTED_ORCID, "authors[0].orcid")

    require_equal(preferred.get("type"), EXPECTED_TYPE, "preferred-citation.type")
    require_equal(preferred.get("title"), release_name, "preferred-citation.title")
    require_equal(preferred.get("version"), release_version, "preferred-citation.version")
    require_equal(preferred.get("doi"), release_doi, "preferred-citation.doi")
    require_equal(preferred.get("year"), release_date[:4], "preferred-citation.year")
    require_equal(preferred.get("url"), release_doi_url, "preferred-citation.url")

    require_equal(codemeta.get("name"), cff.get("title"), "CodeMeta name")
    require_equal(codemeta.get("version"), cff.get("version"), "CodeMeta version")
    require_equal(codemeta.get("identifier"), release_doi_url, "CodeMeta identifier")
    require_equal(codemeta.get("codeRepository"), cff.get("repository-code"), "CodeMeta codeRepository")
    require_equal(codemeta_author.get("@id"), author.get("orcid"), "CodeMeta author @id")

    print("Citation metadata: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
