#!/usr/bin/env python3
# pyright: reportMissingModuleSource=false
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    import atheris
except ImportError:  # pragma: no cover - normal unit-test smoke path.
    atheris = None

from verifier import verify  # noqa: E402


def _exercise_value(value: Any) -> None:
    try:
        verify.canonicalize(value)
    except (TypeError, ValueError, RecursionError):
        return
    if isinstance(value, dict) and isinstance(value.get("policy_decisions"), list):
        try:
            verify.policy_inputs_hash_errors(value)
        except (AttributeError, TypeError, ValueError):
            return
    if isinstance(value, dict) and isinstance(value.get("findings"), list):
        try:
            verify.enforce_profile(value)
        except (AttributeError, KeyError, TypeError, ValueError):
            return


def TestOneInput(data: bytes) -> None:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return
    try:
        value = verify.load_json_no_duplicates(text)
    except (json.JSONDecodeError, ValueError, RecursionError):
        return
    _exercise_value(value)


def main() -> None:
    if atheris is None:
        raise RuntimeError("atheris is required for coverage-guided fuzzing")
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
