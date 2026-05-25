from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

BASE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("verify", BASE / "verifier" / "verify.py")
assert spec is not None and spec.loader is not None
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)

SAFE_MIN = -(2**53) + 1
SAFE_MAX = (2**53) - 1

safe_text = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",)),
    max_size=24,
)
object_key = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",)),
    min_size=1,
    max_size=16,
)
scalar_json = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=SAFE_MIN, max_value=SAFE_MAX),
    safe_text,
)
constrained_json = st.recursive(
    scalar_json,
    lambda children: st.one_of(
        st.lists(children, max_size=4),
        st.dictionaries(object_key, children, max_size=4),
    ),
    max_leaves=12,
)


def load_example(name: str) -> dict[str, Any]:
    return json.loads((BASE / "examples" / name).read_text(encoding="utf-8"))


@given(constrained_json)
@settings(max_examples=80, database=None)
def test_canonicalization_is_deterministic_for_constrained_json(value: Any) -> None:
    assert verify.canonicalize(value) == verify.canonicalize(value)


@given(st.dictionaries(object_key, scalar_json, min_size=2, max_size=8))
@settings(max_examples=60, database=None)
def test_canonicalization_is_independent_of_dict_insertion_order(
    values: dict[str, Any],
) -> None:
    reversed_values = dict(reversed(list(values.items())))

    assert verify.canonicalize(values) == verify.canonicalize(reversed_values)


@given(object_key, scalar_json, scalar_json)
@settings(max_examples=60, database=None)
def test_duplicate_json_members_are_rejected_at_any_object_depth(
    key: str,
    first: Any,
    second: Any,
) -> None:
    encoded_key = json.dumps(key, ensure_ascii=False)
    raw = (
        '{"outer":{'
        f"{encoded_key}:{json.dumps(first, ensure_ascii=False)},"
        f"{encoded_key}:{json.dumps(second, ensure_ascii=False)}"
        "}}"
    )

    with pytest.raises(ValueError, match="Duplicate JSON object member"):
        verify.load_json_no_duplicates(raw)


@given(
    st.one_of(
        st.integers(max_value=SAFE_MIN - 1),
        st.integers(min_value=SAFE_MAX + 1),
    )
)
@settings(max_examples=40, database=None)
def test_canonicalization_rejects_json_unsafe_integers(value: int) -> None:
    with pytest.raises(ValueError, match="safe-integer"):
        verify.canonicalize({"n": value})


@given(st.integers(min_value=0xD800, max_value=0xDFFF))
@settings(max_examples=40, database=None)
def test_canonicalization_rejects_lone_surrogate_code_points(codepoint: int) -> None:
    with pytest.raises(ValueError, match="surrogate"):
        verify.canonicalize({"s": chr(codepoint)})


@given(st.sampled_from(["high", "critical"]), st.sampled_from(["open", "suppressed", "accepted_risk"]))
@settings(max_examples=12, database=None)
def test_unresolved_high_or_critical_findings_never_pass(
    severity: str,
    status: str,
) -> None:
    case = load_example("pass-with-coverage.json")
    case["findings"].append(
        {
            "finding_id": f"generated_{severity}_{status}",
            "category": "generated-adversarial",
            "severity": severity,
            "status": status,
            "subject_asset_id": case["assets"][0]["asset_id"],
            "title": "Generated unresolved finding",
            "created_at": "2026-05-11T13:00:01Z",
            "evidence_refs": [case["evidence_artifacts"][0]["uri"]],
        }
    )

    verdict, _ = verify.recompute_verdict(case)

    assert verdict == ("fail" if severity == "critical" else "hold")


@given(st.sampled_from(["allow", "warn", "hold", "deny"]))
@settings(database=None)
def test_policy_outcome_verdict_effects_are_monotonic(outcome: str) -> None:
    case = load_example("pass-with-coverage.json")
    case["policy_decisions"] = [
        {
            "policy_id": "generated-policy",
            "policy_version": "1.0.0",
            "subject_asset_id": case["assets"][0]["asset_id"],
            "outcome": outcome,
            "inputs_hash": "sha256:" + "0" * 64,
        }
    ]

    verdict, _ = verify.recompute_verdict(case)

    assert verdict == {
        "allow": "pass",
        "warn": "pass",
        "hold": "hold",
        "deny": "fail",
    }[outcome]
