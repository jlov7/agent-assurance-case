"""Check local Markdown and HTML links in repository Markdown files."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote


MARKDOWN_LINK_RE = re.compile(r"!?\[[^\]\n]*\]\(([^)\n]+)\)")
HTML_SRC_RE = re.compile(r"""(?:href|src)=["']([^"']+)["']""", re.IGNORECASE)
SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
SKIP_DIRS = {".git", ".venv"}


def iter_markdown_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*.md"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        files.append(path)
    return sorted(files)


def normalize_target(raw_target: str) -> str | None:
    target = raw_target.strip()
    if target.startswith("<") and ">" in target:
        target = target[1 : target.index(">")]
    else:
        target = target.split()[0]

    if (
        not target
        or target.startswith("#")
        or target.startswith("//")
        or SCHEME_RE.match(target)
    ):
        return None

    target = target.split("#", 1)[0].split("?", 1)[0]
    if not target:
        return None
    return unquote(target)


def local_link_errors(root: Path) -> list[str]:
    errors: list[str] = []
    for markdown_path in iter_markdown_files(root):
        text = markdown_path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), start=1):
            raw_targets = [
                *(match.group(1) for match in MARKDOWN_LINK_RE.finditer(line)),
                *(match.group(1) for match in HTML_SRC_RE.finditer(line)),
            ]
            for raw_target in raw_targets:
                target = normalize_target(raw_target)
                if target is None:
                    continue
                base = root if target.startswith("/") else markdown_path.parent
                linked_path = (base / target.lstrip("/")).resolve()
                try:
                    linked_path.relative_to(root.resolve())
                except ValueError:
                    errors.append(
                        f"{markdown_path}:{line_no}: link escapes repo: {raw_target}"
                    )
                    continue
                if not linked_path.exists():
                    errors.append(
                        f"{markdown_path}:{line_no}: missing local link: {raw_target}"
                    )
    return errors


def main() -> int:
    errors = local_link_errors(Path.cwd())
    if errors:
        print("Markdown local-link check failed:", file=sys.stderr)
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("Markdown local links: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
