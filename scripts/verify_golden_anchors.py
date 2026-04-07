#!/usr/bin/env python3
# ======================================================================
# FSC Policy RAG System | 스크립트: scripts/verify_golden_anchors.py
# 최종 수정일: 2026-04-07
# 연관 문서: CHANGE_CONTROL.md, ROOT_DOC_GUIDE.md, data/golden/parse/README.md
# 참조 규칙: 루트 MD 계약과 충돌 시 CHANGE_CONTROL.md §5 우선.
# ======================================================================

"""골든 reading_order_anchors·structure_checks가 PDF 텍스트에 존재하는지 검증."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
GOLD = ROOT / "data/golden/parse/golden_parse.jsonl"


def main() -> None:
    bad = 0
    for line in GOLD.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        o = json.loads(line)
        fp = ROOT / o["file_path"]
        doc = fitz.open(fp)
        text = "\n".join(doc[i].get_text("text") for i in range(doc.page_count))
        doc.close()
        for a in o.get("reading_order_anchors") or []:
            if a and a not in text:
                print("MISS ro", o["id"], repr(a)[:60])
                bad += 1
        for c in o.get("structure_checks") or []:
            p = c.get("must_appear_before") or []
            if len(p) == 2:
                if p[0] not in text or p[1] not in text:
                    print("MISS sc", o["id"], p)
                    bad += 1
    print("done bad", bad)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
