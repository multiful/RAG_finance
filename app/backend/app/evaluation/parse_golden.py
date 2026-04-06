# ======================================================================
# FSC Policy RAG System | 모듈: app.evaluation.parse_golden
# 최종 수정일: 2026-04-07
# 연관 문서: RAG_PIPELINE.md, EVALUATION_GUIDELINE.md, data/golden/parse/README.md
# ======================================================================

"""Parse 단계 골든셋 로드 및 Exp-1 전용 지표.

논문 프레임: Baseline 대비 Parse 조작만 바꿀 때
reading order / 표 보존 / 구조 검사 / 청크 응집도를 분해 측정한다.
Retriever·rerank·생성은 범위 밖.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_log = logging.getLogger(__name__)


@dataclass
class TableGoldSpec:
    min_rows: int = 2
    min_cols: int = 2
    header_substrings: List[str] = field(default_factory=list)


@dataclass
class StructureCheck:
    """텍스트 내 순서: must_appear_before[0] 이 must_appear_before[1] 보다 먼저 등장."""

    must_appear_before: Tuple[str, str]


@dataclass
class ParseGoldenItem:
    id: str
    file_path: str
    file_type: str = "pdf"
    notes: str = ""
    reading_order_anchors: List[str] = field(default_factory=list)
    table_gold: List[Dict[str, Any]] = field(default_factory=list)
    structure_checks: List[Dict[str, Any]] = field(default_factory=list)
    chunk_quality_unit_groups: List[List[str]] = field(default_factory=list)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "ParseGoldenItem":
        return ParseGoldenItem(
            id=d["id"],
            file_path=d["file_path"],
            file_type=str(d.get("file_type", "pdf")).lower(),
            notes=str(d.get("notes", "")),
            reading_order_anchors=list(d.get("reading_order_anchors") or []),
            table_gold=list(d.get("table_gold") or []),
            structure_checks=list(d.get("structure_checks") or []),
            chunk_quality_unit_groups=list(d.get("chunk_quality_unit_groups") or []),
        )


def load_parse_golden_jsonl(path: Path) -> List[ParseGoldenItem]:
    if not path.is_file():
        raise FileNotFoundError(str(path))
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return []
    out: List[ParseGoldenItem] = []
    for line_no, line in enumerate(raw.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(ParseGoldenItem.from_dict(json.loads(line)))
        except (json.JSONDecodeError, KeyError) as e:
            _log.warning("golden line %s skip: %s", line_no, e)
    return out


def reading_order_pass(text: str, anchors: List[str]) -> bool:
    """앵커가 텍스트 안에서 순서대로(비감소 인덱스) 등장하는지."""
    if not anchors:
        return True
    pos = -1
    body = text or ""
    for a in anchors:
        if not a:
            continue
        idx = body.find(a, pos + 1)
        if idx == -1:
            return False
        pos = idx
    return True


def _table_matches_spec(table: Dict[str, Any], spec: Dict[str, Any]) -> bool:
    headers = [str(h or "") for h in (table.get("headers") or [])]
    rows = table.get("rows") or []
    min_rows = int(spec.get("min_rows", 2))
    min_cols = int(spec.get("min_cols", 2))
    want_headers = list(spec.get("header_substrings") or [])

    row_count = 1 + len(rows) if rows else (1 if headers else 0)
    if row_count < min_rows:
        return False
    if len(headers) < min_cols:
        return False
    hjoin = " ".join(headers).lower()
    for s in want_headers:
        if s.lower() not in hjoin:
            return False
    return True


def table_preservation_pass(parsed_tables: List[Dict[str, Any]], gold_specs: List[Dict[str, Any]]) -> bool:
    """각 gold spec에 대해 하나 이상의 추출 표가 매칭되면 해당 spec 통과."""
    if not gold_specs:
        return True
    for spec in gold_specs:
        ok = any(_table_matches_spec(t, spec) for t in parsed_tables)
        if not ok:
            return False
    return True


def structure_checks_pass(text: str, checks: List[Dict[str, Any]]) -> bool:
    for c in checks:
        pair = c.get("must_appear_before") or []
        if len(pair) != 2:
            continue
        a, b = pair[0], pair[1]
        ia, ib = text.find(a), text.find(b)
        if ia == -1 or ib == -1:
            return False
        if ia >= ib:
            return False
    return True


def chunk_cohesion_pass(chunks: List[str], unit_groups: List[List[str]]) -> bool:
    """각 그룹의 모든 부분 문자열이 같은 청크에 포함되면 해당 그룹 통과."""
    if not unit_groups:
        return True
    for group in unit_groups:
        if not group:
            continue
        found = False
        for ch in chunks:
            if all((g in ch) for g in group if g):
                found = True
                break
        if not found:
            return False
    return True


def evaluate_parsed_document(
    item: ParseGoldenItem,
    parsed: Dict[str, Any],
    chunks_texts: List[str],
) -> Dict[str, Any]:
    """단일 문항에 대한 Pass/지표 딕셔너리."""
    text = (parsed.get("text") or "").strip()
    tables = list(parsed.get("tables") or [])

    ro = reading_order_pass(text, item.reading_order_anchors)
    tp = table_preservation_pass(tables, item.table_gold)
    sc = structure_checks_pass(text, item.structure_checks)
    cq = chunk_cohesion_pass(chunks_texts, item.chunk_quality_unit_groups)

    return {
        "id": item.id,
        "reading_order_pass": ro,
        "table_preservation_pass": tp,
        "structure_check_pass": sc,
        "chunk_cohesion_pass": cq,
        "parser": (parsed.get("metadata") or {}).get("parser"),
        "text_len": len(text),
        "table_count": len(tables),
        "chunk_count": len(chunks_texts),
    }


def aggregate_results(rows: List[Dict[str, Any]]) -> Dict[str, float]:
    if not rows:
        return {
            "n": 0,
            "reading_order_pass_rate": 0.0,
            "table_preservation_rate": 0.0,
            "structure_check_pass_rate": 0.0,
            "chunk_cohesion_rate": 0.0,
        }
    n = len(rows)
    return {
        "n": float(n),
        "reading_order_pass_rate": sum(1 for r in rows if r["reading_order_pass"]) / n,
        "table_preservation_rate": sum(1 for r in rows if r["table_preservation_pass"]) / n,
        "structure_check_pass_rate": sum(1 for r in rows if r["structure_check_pass"]) / n,
        "chunk_cohesion_rate": sum(1 for r in rows if r["chunk_cohesion_pass"]) / n,
    }
