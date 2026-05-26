from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest


BASE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "verify_release_fingerprints",
    BASE / "scripts" / "verify_release_fingerprints.py",
)
assert spec is not None and spec.loader is not None
release_fingerprints = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release_fingerprints)


def _release_evidence() -> dict:
    return json.loads((BASE / "release-evidence.v0.2-candidate.7.json").read_text())


def test_release_evidence_consistency_accepts_current_file() -> None:
    release_fingerprints.validate_release_evidence(_release_evidence())


def test_release_evidence_consistency_rejects_signed_tag_commit_drift() -> None:
    evidence = copy.deepcopy(_release_evidence())
    evidence["signed_tag"]["expected_object"] = "0" * 40

    with pytest.raises(SystemExit, match="signed tag object mismatch"):
        release_fingerprints.validate_release_evidence(evidence)


def test_release_evidence_consistency_rejects_filename_tag_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evidence = _release_evidence()
    monkeypatch.setattr(
        release_fingerprints,
        "RELEASE_EVIDENCE_PATH",
        tmp_path / "release-evidence.v0.2-candidate.8.json",
    )

    with pytest.raises(SystemExit, match="release evidence filename tag mismatch"):
        release_fingerprints.validate_release_evidence(evidence)


def test_release_evidence_consistency_rejects_duplicate_release_asset() -> None:
    evidence = copy.deepcopy(_release_evidence())
    evidence["release_assets"].append(copy.deepcopy(evidence["release_assets"][0]))

    with pytest.raises(SystemExit, match="duplicate release asset names"):
        release_fingerprints.validate_release_evidence(evidence)


def test_release_evidence_consistency_rejects_unexpected_release_asset_name() -> None:
    evidence = copy.deepcopy(_release_evidence())
    evidence["release_assets"][0]["name"] = "unexpected.json"

    with pytest.raises(SystemExit, match="release evidence asset set mismatch"):
        release_fingerprints.validate_release_evidence(evidence)


def test_release_evidence_consistency_rejects_unverified_release_asset() -> None:
    evidence = copy.deepcopy(_release_evidence())
    evidence["release_assets"][0]["github_attestation"] = "missing"

    with pytest.raises(SystemExit, match="attestation status mismatch"):
        release_fingerprints.validate_release_evidence(evidence)
