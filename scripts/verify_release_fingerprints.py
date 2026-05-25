#!/usr/bin/env python3
"""Verify the published AAC release fingerprint from current main."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import venv
from pathlib import Path


REPO_URL = "https://github.com/jlov7/agent-assurance-case"
RELEASE_TAG = "v0.2-candidate.7"
RELEASE_COMMIT = "689198d9c249a966a0abab6415ae8668efb512d9"
SIGNING_PRINCIPAL = "jase.lovell@me.com"
SIGNING_PUBLIC_KEY = (
    "ssh-ed25519 "
    "AAAAC3NzaC1lZDI1NTE5AAAAIBD4r6uZD5gvmyQqXSM/HX3gKtl2+HOzX6T1oaGsUlVu"
)


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


def write_allowed_signers(workdir: Path) -> Path:
    path = workdir / "allowed_signers"
    path.write_text(
        f"{SIGNING_PRINCIPAL} {SIGNING_PUBLIC_KEY} aac-release-signing\n",
        encoding="utf-8",
    )
    return path


def verify_signed_tag(repo: Path, allowed_signers: Path) -> None:
    actual_commit = output(["git", "rev-list", "-n", "1", RELEASE_TAG], cwd=repo)
    if actual_commit != RELEASE_COMMIT:
        raise SystemExit(
            f"{RELEASE_TAG} points to {actual_commit}, expected {RELEASE_COMMIT}"
        )
    run(
        [
            "git",
            "-c",
            f"gpg.ssh.allowedSignersFile={allowed_signers}",
            "tag",
            "-v",
            RELEASE_TAG,
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

    with tempfile.TemporaryDirectory(prefix="aac-release-fingerprint-") as tmp:
        tmp_path = Path(tmp)
        repo = tmp_path / "agent-assurance-case"
        allowed_signers = write_allowed_signers(tmp_path)

        run(
            [
                "git",
                "clone",
                "--branch",
                RELEASE_TAG,
                "--depth",
                "1",
                REPO_URL,
                str(repo),
            ]
        )

        head = output(["git", "rev-parse", "HEAD"], cwd=repo)
        if head != RELEASE_COMMIT:
            raise SystemExit(f"release checkout is {head}, expected {RELEASE_COMMIT}")

        verify_signed_tag(repo, allowed_signers)
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
