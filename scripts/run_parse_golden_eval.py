#!/usr/bin/env python3
"""Parse 골든셋 평가 실행기 (Exp-1).

저장소 루트에서:
  cd app/backend
  python ../../scripts/run_parse_golden_eval.py --golden ../../data/golden/parse/golden_parse.jsonl

루트에서:
  python scripts/run_parse_golden_eval.py
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

# app.backend 를 import path에 넣기
_BACKEND = Path(__file__).resolve().parents[1] / "app" / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
_log = logging.getLogger(__name__)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


async def _parse_one(abs_path: Path, file_type: str) -> dict:
    from app.parsers.llama_parser import get_parser, get_chunker

    parser = get_parser()
    ft = file_type.lower()
    if ft == "html":
        from bs4 import BeautifulSoup

        html = abs_path.read_text(encoding="utf-8", errors="ignore")
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator="\n", strip=True)
        parsed = {
            "text": text,
            "pages": [],
            "tables": [],
            "metadata": {"parser": "beautifulsoup_html", "file_type": "html"},
        }
    else:
        parsed = await parser.parse_file(str(abs_path), "pdf" if ft == "pdf" else ft)

    chunker = get_chunker()
    chunks = chunker.chunk_document(parsed)
    chunk_texts = [c.get("chunk_text", "") for c in chunks]
    return parsed, chunk_texts


async def main_async(args: argparse.Namespace) -> None:
    from app.evaluation.parse_golden import (
        load_parse_golden_jsonl,
        evaluate_parsed_document,
        aggregate_results,
    )

    golden_path = Path(args.golden).resolve()
    items = load_parse_golden_jsonl(golden_path)
    if not items:
        _log.warning("골든셋이 비어 있습니다: %s", golden_path)
        print(json.dumps({"error": "empty golden", "path": str(golden_path)}, ensure_ascii=False, indent=2))
        return

    root = _repo_root()
    rows = []
    for item in items:
        abs_doc = (root / item.file_path).resolve()
        if not abs_doc.is_file():
            _log.error("[%s] 파일 없음: %s", item.id, abs_doc)
            rows.append(
                {
                    "id": item.id,
                    "error": "file_not_found",
                    "path": str(abs_doc),
                    "reading_order_pass": False,
                    "table_preservation_pass": False,
                    "structure_check_pass": False,
                    "chunk_cohesion_pass": False,
                }
            )
            continue
        try:
            parsed, chunk_texts = await _parse_one(abs_doc, item.file_type)
            row = evaluate_parsed_document(item, parsed, chunk_texts)
            rows.append(row)
        except Exception as e:
            _log.exception("[%s] 파싱 실패", item.id)
            rows.append(
                {
                    "id": item.id,
                    "error": str(e),
                    "reading_order_pass": False,
                    "table_preservation_pass": False,
                    "structure_check_pass": False,
                    "chunk_cohesion_pass": False,
                }
            )

    agg = aggregate_results([r for r in rows if "error" not in r])
    out = {"aggregate": agg, "items": rows}
    if args.out:
        Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        _log.info("저장: %s", args.out)
    else:
        print(json.dumps(out, ensure_ascii=False, indent=2))


def main() -> None:
    p = argparse.ArgumentParser(description="Parse golden eval (Exp-1)")
    p.add_argument(
        "--golden",
        default=str(_repo_root() / "data" / "golden" / "parse" / "golden_parse.jsonl"),
        help="golden_parse.jsonl 경로",
    )
    p.add_argument("--out", default="", help="결과 JSON 저장 경로(미지정 시 stdout)")
    args = p.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
