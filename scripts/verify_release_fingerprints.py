#!/usr/bin/env python3
"""Verify the published AAC release fingerprint from current main."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import venv
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RELEASE_EVIDENCE_PATH = ROOT / "release-evidence.v0.2-candidate.7.json"


def run(
    command: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> None:
    print(f"$ {' '.join(command)}", flush=True)
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    subprocess.run(command, cwd=cwd, env=merged_env, check=True)


def output(command: list[str], *, cwd: Path) -> str:
    return subprocess.check_output(command, cwd=cwd, text=True).strip()


def require_tool(name: str) -> None:
    if shutil.which(name) is None:
        raise SystemExit(f"required tool not found on PATH: {name}")


def load_release_evidence() -> dict[str, Any]:
    return json.loads(RELEASE_EVIDENCE_PATH.read_text(encoding="utf-8"))


def require_equal(label: str, actual: str, expected: str) -> None:
    if actual != expected:
        raise SystemExit(f"{label} mismatch: {actual} != {expected}")


def validate_release_evidence(evidence: dict[str, Any]) -> None:
    release = evidence["release"]
    signed_tag = evidence["signed_tag"]
    require_equal(
        "signed tag object",
        str(signed_tag["expected_object"]),
        str(release["release_commit"]),
    )
    require_equal(
        "release evidence filename tag",
        str(release["tag"]),
        RELEASE_EVIDENCE_PATH.stem.removeprefix("release-evidence."),
    )


def write_allowed_signers(
    workdir: Path,
    *,
    principal: str,
    public_key: str,
) -> Path:
    path = workdir / "allowed_signers"
    path.write_text(
        f"{principal} {public_key} aac-release-signing\n",
        encoding="utf-8",
    )
    return path


def verify_signed_tag(
    repo: Path,
    *,
    tag: str,
    expected_commit: str,
    allowed_signers: Path,
) -> None:
    actual_commit = output(["git", "rev-list", "-n", "1", tag], cwd=repo)
    if actual_commit != expected_commit:
        raise SystemExit(
            f"{tag} points to {actual_commit}, expected {expected_commit}"
        )
    run(
        [
            "git",
            "-c",
            f"gpg.ssh.allowedSignersFile={allowed_signers}",
            "tag",
            "-v",
            tag,
        ],
        cwd=repo,
    )


def create_python_env(repo: Path, env_dir: Path) -> Path:
    venv.EnvBuilder(with_pip=True).create(env_dir)
    python = env_dir / "bin" / "python"
    run([str(python), "-m", "pip", "install", "--upgrade", "pip"], cwd=repo)
    run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "-r",
            "verifier/requirements.txt",
            "-r",
            "verifier/requirements-dev.txt",
        ],
        cwd=repo,
    )
    return python


def main() -> int:
    require_tool("git")
    require_tool("bash")
    evidence = load_release_evidence()
    validate_release_evidence(evidence)
    release = evidence["release"]
    signed_tag = evidence["signed_tag"]
    repo_url = str(release["repository"])
    release_tag = str(release["tag"])
    release_commit = str(release["release_commit"])
    signing_principal = str(signed_tag["signer"])
    signing_public_key = str(signed_tag["public_key"])

    with tempfile.TemporaryDirectory(prefix="aac-release-fingerprint-") as tmp:
        tmp_path = Path(tmp)
        repo = tmp_path / "agent-assurance-case"
        allowed_signers = write_allowed_signers(
            tmp_path,
            principal=signing_principal,
            public_key=signing_public_key,
        )

        run(
            [
                "git",
                "clone",
                "--branch",
                release_tag,
                "--depth",
                "1",
                repo_url,
                str(repo),
            ]
        )

        head = output(["git", "rev-parse", "HEAD"], cwd=repo)
        if head != release_commit:
            raise SystemExit(f"release checkout is {head}, expected {release_commit}")

        verify_signed_tag(
            repo,
            tag=release_tag,
            expected_commit=release_commit,
            allowed_signers=allowed_signers,
        )
        python = create_python_env(repo, tmp_path / "fingerprint-venv")

        gate_env = {
            "PYTHON": str(python),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
            "PIP_NO_CACHE_DIR": "1",
        }
        run(["bash", "./VERIFY-PUBLICATION-READY.sh"], cwd=repo, env=gate_env)
        run([str(python), "verifier/check_vectors.py"], cwd=repo)

        for example in (
            "pass-with-coverage",
            "skill-poisoning-hold",
            "critical-exfiltration-fail",
        ):
            run(
                [
                    str(python),
                    "verifier/verify.py",
                    f"examples/{example}.json",
                    "--allow-demo-key",
                ],
                cwd=repo,
                env={"PYTHONDONTWRITEBYTECODE": "1"},
            )

    print("AAC release fingerprint: valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
