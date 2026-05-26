#!/usr/bin/env python3
"""Verify the published AAC release fingerprint from current main."""

from __future__ import annotations

import json
import os
import hashlib
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
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
    asset_names = [asset["name"] for asset in evidence["release_assets"]]
    if len(asset_names) != len(set(asset_names)):
        raise SystemExit("release evidence contains duplicate release asset names")
    release_version = str(release["tag"]).removeprefix("v")
    expected_asset_names = {
        "RELEASE-MANIFEST.json",
        "SHA256SUMS",
        f"agent-assurance-case-v{release_version}.tar.gz",
        f"agent-assurance-case-v{release_version}.tar.gz.sha256",
    }
    if set(asset_names) != expected_asset_names:
        raise SystemExit(
            "release evidence asset set mismatch: "
            f"{sorted(asset_names)} != {sorted(expected_asset_names)}"
        )
    for asset in evidence["release_assets"]:
        require_equal(
            f"{asset['name']} attestation status",
            str(asset["github_attestation"]),
            "verified",
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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_release_assets(
    destination: Path,
    *,
    asset_base_url: str,
    asset_digests: dict[str, str],
) -> None:
    destination.mkdir(parents=True)
    for name, expected_digest in asset_digests.items():
        url = f"{asset_base_url}/{name}"
        parsed_url = urllib.parse.urlparse(url)
        if parsed_url.scheme != "https" or parsed_url.netloc != "github.com":
            raise SystemExit(f"refusing non-GitHub HTTPS release asset URL: {url}")
        target = destination / name
        print(f"download {url}", flush=True)
        with urllib.request.urlopen(url, timeout=30) as response:  # nosec B310
            target.write_bytes(response.read())
        actual_digest = sha256(target)
        if actual_digest != expected_digest:
            raise SystemExit(
                f"{name} sha256 mismatch: {actual_digest} != {expected_digest}"
            )


def verify_sha256s(assets_dir: Path, sums_name: str) -> None:
    sums_path = assets_dir / sums_name
    for line in sums_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected_digest, relative_path = line.split(maxsplit=1)
        target = assets_dir / relative_path
        if not target.is_file():
            raise SystemExit(f"{sums_name} target missing: {relative_path}")
        actual_digest = sha256(target)
        if actual_digest != expected_digest:
            raise SystemExit(
                f"{relative_path} sha256 mismatch: "
                f"{actual_digest} != {expected_digest}"
            )


def verify_release_asset_attestations(
    assets_dir: Path,
    *,
    repo: str,
    asset_names: list[str],
) -> None:
    require_tool("gh")
    for name in asset_names:
        run(
            [
                "gh",
                "attestation",
                "verify",
                str(assets_dir / name),
                "--repo",
                repo,
            ],
        )


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
    asset_digests = {
        asset["name"]: asset["github_asset_digest"].removeprefix("sha256:")
        for asset in evidence["release_assets"]
    }
    asset_base_url = f"{release['repository']}/releases/download/{release['tag']}"

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

        assets_dir = tmp_path / "release-assets"
        download_release_assets(
            assets_dir,
            asset_base_url=asset_base_url,
            asset_digests=asset_digests,
        )
        verify_sha256s(assets_dir, "SHA256SUMS")
        verify_sha256s(
            assets_dir,
            f"agent-assurance-case-{release_tag}.tar.gz.sha256",
        )
        verify_release_asset_attestations(
            assets_dir,
            repo="jlov7/agent-assurance-case",
            asset_names=sorted(asset_digests),
        )

    print("AAC release fingerprint: valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
