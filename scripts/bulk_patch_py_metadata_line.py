#!/usr/bin/env python3
# ======================================================================
# FSC Policy RAG System | 스크립트: scripts/bulk_patch_py_metadata_line.py
# 최종 수정일: 2026-04-07
# 연관 문서: CHANGE_CONTROL.md, ROOT_DOC_GUIDE.md, scripts/inject_python_metadata.py
# 참조 규칙: 루트 MD 계약과 충돌 시 CHANGE_CONTROL.md §5 우선.
# ======================================================================

"""기존 4행 메타 블록에 CHANGE_CONTROL·참조 규칙 줄을 삽입 (일회성 마이그레이션)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app" / "backend" / "app"
OLD = (
    "# 연관 문서: SYSTEM_ARCHITECTURE.md, RAG_PIPELINE.md, DIRECTORY_SPEC.md\n"
    "# " + "=" * 70 + "\n"
)
NEW = (
    "# 연관 문서: CHANGE_CONTROL.md, ROOT_DOC_GUIDE.md, SYSTEM_ARCHITECTURE.md, RAG_PIPELINE.md, DIRECTORY_SPEC.md\n"
    "# 참조 규칙: 루트 MD 계약과 충돌 시 CHANGE_CONTROL.md §5 우선.\n"
    "# " + "=" * 70 + "\n"
)


def main() -> None:
    n = 0
    for p in sorted(APP.rglob("*.py")):
        if "__pycache__" in p.parts:
            continue
        t = p.read_text(encoding="utf-8")
        if OLD not in t:
            continue
        p.write_text(t.replace(OLD, NEW, 1), encoding="utf-8")
        n += 1
    print("patched", n, "files")


if __name__ == "__main__":
    main()
