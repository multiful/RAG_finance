#!/usr/bin/env python3
# ======================================================================
# FSC Policy RAG System | 스크립트: scripts/inject_python_metadata.py
# 최종 수정일: 2026-04-07
# 연관 문서: CHANGE_CONTROL.md, ROOT_DOC_GUIDE.md, DIRECTORY_SPEC.md
# 참조 규칙: 루트 MD 계약과 충돌 시 CHANGE_CONTROL.md §5 우선.
# ======================================================================

"""app/backend/app/**/*.py 파일 상단에 FSC Policy RAG 모듈 메타 주석을 삽입한다.

이미 `FSC Policy RAG System | 모듈:` 마커가 있으면 건너뛴다.
"""
from __future__ import annotations

import re
from pathlib import Path

BACKEND_APP = Path(__file__).resolve().parents[1] / "app" / "backend" / "app"
MARKER = "FSC Policy RAG System | 모듈:"


def module_qualname(py_path: Path) -> str:
    rel = py_path.relative_to(BACKEND_APP.parent).with_suffix("")
    parts = rel.parts
    return ".".join(parts)


def build_block(mod: str) -> str:
    line = "# " + "=" * 70
    return (
        f"{line}\n"
        f"# FSC Policy RAG System | 모듈: {mod}\n"
        f"# 최종 수정일: 2026-04-07\n"
        f"# 연관 문서: CHANGE_CONTROL.md, ROOT_DOC_GUIDE.md, SYSTEM_ARCHITECTURE.md, RAG_PIPELINE.md, DIRECTORY_SPEC.md\n"
        f"# 참조 규칙: 루트 MD 계약과 충돌 시 CHANGE_CONTROL.md §5 우선.\n"
        f"{line}\n\n"
    )


def insert_metadata(content: str, mod: str) -> str | None:
    if MARKER in content[:4000]:
        return None
    block = build_block(mod)
    lines = content.splitlines(keepends=True)
    i = 0
    if lines and lines[0].startswith("#!"):
        i = 1
    while i < len(lines) and "coding:" in lines[i] and lines[i].startswith("#"):
        i += 1
    while i < len(lines):
        s = lines[i].strip()
        if s.startswith("from __future__"):
            i += 1
            continue
        break
    return "".join(lines[:i]) + block + "".join(lines[i:])


def main() -> None:
    if not BACKEND_APP.is_dir():
        raise SystemExit(f"missing {BACKEND_APP}")
    n = 0
    for path in sorted(BACKEND_APP.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        mod = module_qualname(path)
        new = insert_metadata(text, mod)
        if new is None:
            continue
        path.write_text(new, encoding="utf-8")
        n += 1
        print("updated", path.relative_to(BACKEND_APP.parent))
    print("total", n)


if __name__ == "__main__":
    main()
