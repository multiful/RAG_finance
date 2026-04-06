#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Markdown **문서 해시** SHA-256 갱신. 기본=루트 `*.md`, `--all-md`=전체(제외 디렉터리 제외)."""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        "node_modules",
        ".venv",
        "venv",
        "__pycache__",
        "dist",
        ".pytest_cache",
        ".mypy_cache",
    }
)
HASH_LINE_RE = re.compile(
    r"(\*\*문서 해시\*\*:\s*SHA256:)[a-fA-F0-9]{64}(\s*\r?\n?)",
    re.MULTILINE,
)


def content_for_hash(text: str) -> str:
    return HASH_LINE_RE.sub(r"\1\2", text, count=1)


def update_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if "**문서 해시**" not in text:
        return False
    if not HASH_LINE_RE.search(text):
        return False
    basis = content_for_hash(text)
    digest = hashlib.sha256(basis.encode("utf-8")).hexdigest()
    new_text = HASH_LINE_RE.sub(
        lambda m: f"{m.group(1)}{digest}{m.group(2)}",
        text,
        count=1,
    )
    if new_text == text:
        return False
    path.write_text(new_text, encoding="utf-8")
    return True


def iter_all_markdown() -> list[Path]:
    out: list[Path] = []
    for p in ROOT.rglob("*.md"):
        rel = p.relative_to(ROOT)
        if any(part in SKIP_DIR_NAMES for part in rel.parts):
            continue
        out.append(p)
    return sorted(out)


def main() -> None:
    use_all = "--all-md" in sys.argv
    paths = iter_all_markdown() if use_all else sorted(ROOT.glob("*.md"))
    for path in paths:
        if update_file(path):
            print("updated", path.relative_to(ROOT) if use_all else path.name)


if __name__ == "__main__":
    main()
