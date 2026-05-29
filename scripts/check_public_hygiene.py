"""Reject public-artifact hygiene regressions in tracked repository files."""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Rule:
    name: str
    pattern: re.Pattern[str]


RULES = [
    Rule("local macOS user path", re.compile(r"/Users/[A-Za-z0-9._-]+")),
    Rule("local Windows user path", re.compile(r"[A-Za-z]:\\Users\\")),
    Rule("private workspace name", re.compile(r"Runwright Agent Assurance Platform")),
    Rule("OpenAI API key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")),
    Rule(
        "GitHub token",
        re.compile(r"\b(?:ghp|gho|ghu|ghs|github_pat)_[A-Za-z0-9_]{20,}\b"),
    ),
    Rule("API key environment variable", re.compile(r"\bOPENAI_API_KEY\b")),
    Rule("first-person employer framing", re.compile(r"\bmy employer\b", re.I)),
    Rule(
        "hype wording",
        re.compile(
            r"\b(?:world-class|elite|frontier|cutting-edge|state-of-the-art|"
            r"revolutionary|game-?changing|best-in-class|industry-leading|"
            r"unparalleled|groundbreaking)\b",
            re.I,
        ),
    ),
]

PRIVATE_PASSPHRASE = "vh84" + "uZod" + "ZSZFHU0"
SKIP_SUFFIXES = {
    ".gif",
    ".gz",
    ".ico",
    ".jpeg",
    ".jpg",
    ".pdf",
    ".png",
    ".tar",
    ".webp",
    ".zip",
}


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        check=True,
        stdout=subprocess.PIPE,
    )
    return [Path(item.decode()) for item in result.stdout.split(b"\0") if item]


def read_text(path: Path) -> str | None:
    if path.suffix.lower() in SKIP_SUFFIXES:
        return None
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None


def hygiene_errors() -> list[str]:
    errors: list[str] = []
    for path in tracked_files():
        if path == Path("scripts/check_public_hygiene.py"):
            continue
        text = read_text(path)
        if text is None:
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            if PRIVATE_PASSPHRASE in line:
                errors.append(f"{path}:{line_no}: private passphrase literal")
            for rule in RULES:
                if rule.pattern.search(line):
                    errors.append(f"{path}:{line_no}: {rule.name}")
    return errors


def main() -> int:
    errors = hygiene_errors()
    if errors:
        print("Public hygiene check failed:", file=sys.stderr)
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("Public hygiene: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
