from __future__ import annotations

import importlib.util
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]


def _load_harness(name: str):
    spec = importlib.util.spec_from_file_location(name, BASE / "fuzz" / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_aac_verifier_fuzzer_seed_inputs_do_not_crash() -> None:
    harness = _load_harness("aac_verifier_fuzzer")

    for seed in (
        b"",
        b"{",
        b'{"schema_version":"0.2","schema_version":"0.2"}',
        b'{"n":9007199254740992}',
        b'{"evidence":{"signed_at":"2026-05-11T13:00:00Z"},"findings":[]}',
    ):
        harness.TestOneInput(seed)
