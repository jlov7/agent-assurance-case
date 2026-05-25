#!/usr/bin/env python3
"""Check AAC v0.2 canonicalization and sign/verify conformance vectors."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import verify


ROOT = Path(__file__).resolve().parent.parent
CANONICALIZATION_VECTORS = ROOT / "test-vectors" / "canonicalization-v0.2.json"
SIGN_VERIFY_VECTOR = ROOT / "test-vectors" / "sign-verify-v0.2.json"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _check_canonicalization_vectors() -> tuple[int, int, list[str]]:
    vectors = _load_json(CANONICALIZATION_VECTORS)
    errors: list[str] = []

    for vector in vectors["accept"]:
        name = vector["name"]
        try:
            actual = verify.canonicalize(vector["value"])
        except Exception as exc:  # pragma: no cover - defensive report path
            errors.append(f"canonicalization accept/{name}: unexpected error: {exc}")
            continue
        expected = vector["canonical"].encode("utf-8")
        expected_hex = vector["canonical_utf8_hex"]
        if actual != expected:
            errors.append(
                f"canonicalization accept/{name}: bytes mismatch "
                f"expected={expected.hex()} actual={actual.hex()}"
            )
        if actual.hex() != expected_hex:
            errors.append(
                f"canonicalization accept/{name}: hex mismatch "
                f"expected={expected_hex} actual={actual.hex()}"
            )

    for vector in vectors["reject"]:
        name = vector["name"]
        try:
            verify.canonicalize(vector["value"])
        except Exception as exc:
            if vector["error_contains"] not in str(exc):
                errors.append(
                    f"canonicalization reject/{name}: wrong error "
                    f"expected substring={vector['error_contains']!r} actual={exc!r}"
                )
        else:
            errors.append(f"canonicalization reject/{name}: unexpectedly accepted")

    return len(vectors["accept"]), len(vectors["reject"]), errors


def _check_sign_verify_vector() -> tuple[str, list[str]]:
    vector = _load_json(SIGN_VERIFY_VECTOR)
    vector_id = vector["vector_id"]
    errors: list[str] = []

    case_path = ROOT / vector["case_file"]
    case = verify.load_json_no_duplicates(case_path.read_text(encoding="utf-8"))

    expected_payload_hex = "".join(vector["canonical_payload_utf8_hex_chunks"])
    actual_payload_hex = verify.payload_bytes(case).hex()
    if actual_payload_hex != expected_payload_hex:
        errors.append(
            f"sign-verify/{vector_id}: canonical payload mismatch "
            f"expected={expected_payload_hex} actual={actual_payload_hex}"
        )

    actual_hash = verify.compute_content_hash(case)
    if actual_hash != vector["content_hash"]:
        errors.append(
            f"sign-verify/{vector_id}: content hash mismatch "
            f"expected={vector['content_hash']} actual={actual_hash}"
        )

    evidence = case["evidence"]
    for field in ("signature_algorithm", "canonicalization", "signature"):
        if evidence.get(field) != vector[field]:
            errors.append(
                f"sign-verify/{vector_id}: evidence.{field} mismatch "
                f"expected={vector[field]} actual={evidence.get(field)}"
            )

    public_key = verify.load_public_key(ROOT / vector["public_key_file"])
    if not verify.verify_signature(public_key, case):
        errors.append(f"sign-verify/{vector_id}: signature verification failed")

    return vector_id, errors


def check_vectors() -> list[str]:
    _, _, canonicalization_errors = _check_canonicalization_vectors()
    _, sign_verify_errors = _check_sign_verify_vector()
    return canonicalization_errors + sign_verify_errors


def main() -> int:
    accept_count, reject_count, canonicalization_errors = (
        _check_canonicalization_vectors()
    )
    vector_id, sign_verify_errors = _check_sign_verify_vector()
    errors = canonicalization_errors + sign_verify_errors

    print(f"AAC vectors: canonicalization accept={accept_count} reject={reject_count}")
    print(f"AAC vectors: sign_verify={vector_id}")

    if errors:
        print("AAC vectors: NOT VALID")
        for error in errors:
            print(f"- {error}")
        return 1

    print("AAC vectors: valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
