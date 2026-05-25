#!/usr/bin/env python3
"""Validate the committed AAC runtime dependency SBOM."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS_PATH = ROOT / "verifier" / "requirements.txt"
SBOM_PATH = ROOT / "sbom" / "runtime-requirements.cdx.json"

REQUIREMENT_RE = re.compile(r"^(?P<name>[A-Za-z0-9_.-]+)>=(?P<version>[A-Za-z0-9_.!+-]+)$")


def fail(message: str) -> NoReturn:
    print(f"Dependency SBOM invalid: {message}", file=sys.stderr)
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


def require_list(value: object, field: str) -> list[object]:
    if not isinstance(value, list):
        fail(f"{field} must be an array")
    return value


def require_mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        fail(f"{field} must be an object")
    return value


def runtime_requirements() -> dict[str, tuple[int, str]]:
    requirements: dict[str, tuple[int, str]] = {}
    for line_number, raw_line in enumerate(REQUIREMENTS_PATH.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = REQUIREMENT_RE.fullmatch(line)
        if match is None:
            fail(f"unsupported requirement line {line_number}: {line!r}")
        name = match.group("name").lower().replace("_", "-")
        if name in requirements:
            fail(f"duplicate runtime requirement: {name}")
        requirements[name] = (line_number, line)
    return requirements


def component_distribution_url(component: Mapping[str, object]) -> str:
    for item in require_list(component.get("externalReferences"), "component.externalReferences"):
        reference = require_mapping(item, "component.externalReferences[]")
        if reference.get("type") == "distribution":
            url = reference.get("url")
            if isinstance(url, str):
                return url
    fail(f"component {component.get('name')!r} missing distribution URL")


def main() -> int:
    requirements = runtime_requirements()
    sbom = load_json(SBOM_PATH)

    if sbom.get("bomFormat") != "CycloneDX":
        fail("bomFormat must be CycloneDX")
    if sbom.get("specVersion") != "1.6":
        fail("specVersion must be 1.6")

    metadata = require_mapping(sbom.get("metadata"), "metadata")
    properties = require_list(metadata.get("properties"), "metadata.properties")
    if {"name": "cdx:reproducible", "value": "true"} not in properties:
        fail("metadata.properties must include cdx:reproducible=true")

    components = require_list(sbom.get("components"), "components")
    observed: dict[str, Mapping[str, object]] = {}
    for item in components:
        component = require_mapping(item, "components[]")
        name = component.get("name")
        if not isinstance(name, str):
            fail("component.name must be a string")
        normalized_name = name.lower().replace("_", "-")
        if normalized_name in observed:
            fail(f"duplicate component: {normalized_name}")
        observed[normalized_name] = component

    if set(observed) != set(requirements):
        fail(f"components {sorted(observed)} do not match requirements {sorted(requirements)}")

    component_refs: set[str] = set()
    for name, component in observed.items():
        line_number, requirement = requirements[name]
        bom_ref = component.get("bom-ref")
        if not isinstance(bom_ref, str):
            fail(f"{name} missing bom-ref")
        component_refs.add(bom_ref)
        if component.get("type") != "library":
            fail(f"{name} type must be library")
        if component.get("version") is not None:
            fail(f"{name} must not declare a pinned version in the requirements SBOM")
        expected_description = f"requirements line {line_number}: {requirement}"
        if component.get("description") != expected_description:
            fail(f"{name} description must be {expected_description!r}")
        expected_purl = f"pkg:pypi/{name}"
        if component.get("purl") != expected_purl:
            fail(f"{name} purl must be {expected_purl!r}")
        expected_url = f"https://pypi.org/simple/{name}/"
        if component_distribution_url(component) != expected_url:
            fail(f"{name} distribution URL must be {expected_url!r}")

    dependencies = require_list(sbom.get("dependencies"), "dependencies")
    dependency_refs = {require_mapping(item, "dependencies[]").get("ref") for item in dependencies}
    if dependency_refs != component_refs:
        fail("dependencies must contain one entry for each component bom-ref")

    print("Dependency SBOM: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
