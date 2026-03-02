"""
Risk–Policy Gap Map 서비스 (스테이블코인·STO 결합 환경, KAI 문서 기준).

- 의미: GI=국제적 중요도, LC=국내 법제 커버리지. Gap=GI×(1-LC) → 국제 기준에 비해 국내가 미흡한 정도.
- Gap이 큰 축 = 국제적으로는 중요한데 우리나라 규제 보완이 미흡한 축(우선 보완 대상).
- DB 우선: gap_map_scores에서 GI/LC 조회, 없으면 상수 fallback.
- get_top_blind_spots(limit): Gap 상위 N개 = 국제 대비 국내 규제 미흡 축.
- lc_evidence: 마이그레이션(gap_map_lc_evidence.sql) 미실행 시 조회/갱신 시 폴백 동작.
"""
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

from app.constants.risk_axes import (
    RISK_AXIS_IDS,
    RISK_AXIS_NAMES,
    RISK_AXIS_DESCRIPTIONS,
    RISK_AXIS_INITIAL_GI_LC,
)
from app.models.gap_map_schemas import (
    RiskAxisScore,
    BlindSpotItem,
    GapMapHeatmapRow,
)


def _compute_gap(gi: float, lc: float) -> float:
    """Gap = GI × (1 - LC) (KAI page_5, page_18)."""
    return round(gi * (1.0 - lc), 4)


def _compute_gi_from_components(freq: float, rec: float, inc: float, sys: float) -> float:
    """GI = 0.3·Freq + 0.3·Rec + 0.2·Inc + 0.2·Sys (0~1)."""
    return round(0.3 * freq + 0.3 * rec + 0.2 * inc + 0.2 * sys, 4)


def _load_scores_from_db() -> Optional[dict]:
    """Supabase gap_map_scores에서 축별 gi/lc/lc_evidence 조회. lc_evidence 컬럼 없으면 gi/lc/source_or_note만."""
    try:
        from app.core.database import get_db
        db = get_db()
        r = db.table("gap_map_scores").select("axis_id, gi, lc, source_or_note, lc_evidence").execute()
        if not r.data or len(r.data) == 0:
            return None
        return {
            row["axis_id"]: {
                "gi": float(row["gi"]),
                "lc": float(row["lc"]),
                "source_or_note": row.get("source_or_note"),
                "lc_evidence": row.get("lc_evidence"),
            }
            for row in r.data
        }
    except Exception as e:
        logger.debug("gap_map_scores: lc_evidence 포함 select 실패, 컬럼 없음 폴백 사용. %s", e)
        try:
            from app.core.database import get_db
            db = get_db()
            r = db.table("gap_map_scores").select("axis_id, gi, lc, source_or_note").execute()
            if not r.data or len(r.data) == 0:
                return None
            return {
                row["axis_id"]: {
                    "gi": float(row["gi"]),
                    "lc": float(row["lc"]),
                    "source_or_note": row.get("source_or_note"),
                    "lc_evidence": None,
                }
                for row in r.data
            }
        except Exception:
            return None


def _load_gi_components_from_db() -> Optional[dict]:
    """gap_map_gi_components에서 축별 freq/rec/inc/sys/source_doc 조회. 없거나 실패 시 None."""
    try:
        from app.core.database import get_db
        db = get_db()
        r = db.table("gap_map_gi_components").select("axis_id, freq, rec, inc, sys, source_doc").execute()
        if not r.data or len(r.data) == 0:
            return None
        return {
            row["axis_id"]: {
                "freq": float(row["freq"]), "rec": float(row["rec"]),
                "inc": float(row["inc"]), "sys": float(row["sys"]),
                "source_doc": row.get("source_doc"),
            }
            for row in r.data
        }
    except Exception:
        return None


def get_gap_map_fallback() -> List[RiskAxisScore]:
    """DB 없이 상수(RISK_AXIS_INITIAL_GI_LC)만으로 Gap Map 반환. API 예외 시 사용."""
    result: List[RiskAxisScore] = []
    for axis_id in RISK_AXIS_IDS:
        row = next((r for r in RISK_AXIS_INITIAL_GI_LC if r["axis_id"] == axis_id), None)
        if not row:
            continue
        gi, lc = row["gi"], row["lc"]
        gap = _compute_gap(gi, lc)
        name_ko = RISK_AXIS_NAMES.get(axis_id, axis_id)
        result.append(RiskAxisScore(axis_id=axis_id, name_ko=name_ko, gi=gi, lc=lc, gap=gap))
    return result


def get_gap_map() -> List[RiskAxisScore]:
    """10개 리스크 축에 대해 GI, LC, Gap 계산.
    GI: gap_map_gi_components 있으면 공식으로 계산, 없으면 gap_map_scores.gi → 상수 fallback.
    LC: gap_map_scores 우선, 없으면 상수 fallback.
    """
    db_scores = _load_scores_from_db()
    gi_components = _load_gi_components_from_db()
    result: List[RiskAxisScore] = []
    for axis_id in RISK_AXIS_IDS:
        if gi_components and axis_id in gi_components:
            c = gi_components[axis_id]
            gi = _compute_gi_from_components(c["freq"], c["rec"], c["inc"], c["sys"])
        elif db_scores and axis_id in db_scores:
            gi = db_scores[axis_id]["gi"]
        else:
            row = next((r for r in RISK_AXIS_INITIAL_GI_LC if r["axis_id"] == axis_id), None)
            if not row:
                continue
            gi = row["gi"]
        if db_scores and axis_id in db_scores:
            lc = db_scores[axis_id]["lc"]
        else:
            row = next((r for r in RISK_AXIS_INITIAL_GI_LC if r["axis_id"] == axis_id), None)
            lc = row["lc"] if row else 0.5
        gap = _compute_gap(gi, lc)
        name_ko = RISK_AXIS_NAMES.get(axis_id, axis_id)
        result.append(
            RiskAxisScore(axis_id=axis_id, name_ko=name_ko, gi=gi, lc=lc, gap=gap)
        )
    return result


def get_top_blind_spots(limit: int = 3) -> List[BlindSpotItem]:
    """Gap 상위 N개 사각지대 반환 (R3, R2, R5 등)."""
    full = get_gap_map()
    sorted_by_gap = sorted(full, key=lambda x: x.gap, reverse=True)
    top = sorted_by_gap[:limit]
    return [
        BlindSpotItem(
            rank=i + 1,
            axis_id=item.axis_id,
            name_ko=item.name_ko,
            gap=item.gap,
            description=RISK_AXIS_DESCRIPTIONS.get(item.axis_id, ""),
        )
        for i, item in enumerate(top)
    ]


def get_heatmap_data() -> List[GapMapHeatmapRow]:
    """Heatmap용 2차원 데이터 (축별 GI/LC/Gap)."""
    return [
        GapMapHeatmapRow(
            axis_id=s.axis_id,
            name_ko=s.name_ko,
            gi=s.gi,
            lc=s.lc,
            gap=s.gap,
        )
        for s in get_gap_map()
    ]


def update_scores(
    axis_id: str,
    gi: Optional[float] = None,
    lc: Optional[float] = None,
    source_or_note: Optional[str] = None,
    lc_evidence: Optional[str] = None,
) -> bool:
    """한 축의 GI/LC/LC근거 수정. 성공 시 True."""
    if axis_id not in RISK_AXIS_IDS:
        return False
    payload = {}
    if gi is not None:
        payload["gi"] = max(0.0, min(1.0, gi))
    if lc is not None:
        payload["lc"] = max(0.0, min(1.0, lc))
    if source_or_note is not None:
        payload["source_or_note"] = source_or_note
    if lc_evidence is not None:
        payload["lc_evidence"] = lc_evidence
    if not payload:
        return True
    try:
        from app.core.database import get_db
        get_db().table("gap_map_scores").update(payload).eq("axis_id", axis_id).execute()
        return True
    except Exception as e:
        if "lc_evidence" in payload:
            logger.debug("gap_map_scores update: lc_evidence 컬럼 없음 폴백. axis_id=%s, %s", axis_id, e)
            from app.core.database import get_db
            payload = {k: v for k, v in payload.items() if k != "lc_evidence"}
            if payload:
                try:
                    get_db().table("gap_map_scores").update(payload).eq("axis_id", axis_id).execute()
                    return True
                except Exception:
                    pass
        return False


def get_lc_evidence_all() -> List[dict]:
    """전체 축의 LC 근거 목록 (근거 보기/내보내기용). axis_id, name_ko, lc, lc_evidence, source_or_note."""
    db_scores = _load_scores_from_db()
    result = []
    for axis_id in RISK_AXIS_IDS:
        name_ko = RISK_AXIS_NAMES.get(axis_id, axis_id)
        row = db_scores.get(axis_id) if db_scores else None
        lc = float(row["lc"]) if row else 0.5
        lc_evidence = (row.get("lc_evidence") or "") if row else ""
        source_or_note = (row.get("source_or_note") or "") if row else ""
        result.append({
            "axis_id": axis_id,
            "name_ko": name_ko,
            "lc": lc,
            "lc_evidence": lc_evidence,
            "source_or_note": source_or_note,
        })
    return result


def upsert_scores_bulk(scores: List[dict]) -> bool:
    """여러 축 일괄 upsert. scores = [{"axis_id":"R1","gi":0.5,"lc":0.5}, ...]. 성공 시 True.
    lc_evidence 컬럼 없으면 행별/전체 폴백으로 lc_evidence 제외 후 재시도."""
    from app.core.database import get_db

    def _payloads_with_evidence() -> List[dict]:
        out = []
        for row in scores:
            axis_id = row.get("axis_id")
            if axis_id not in RISK_AXIS_IDS:
                continue
            gi = max(0.0, min(1.0, float(row.get("gi", 0))))
            lc = max(0.0, min(1.0, float(row.get("lc", 0))))
            note = row.get("source_or_note")
            evidence = row.get("lc_evidence")
            p = {"axis_id": axis_id, "gi": gi, "lc": lc, "source_or_note": note}
            if evidence is not None:
                p["lc_evidence"] = evidence
            out.append(p)
        return out

    payloads = _payloads_with_evidence()
    if not payloads:
        return True

    try:
        db = get_db()
        for payload in payloads:
            try:
                db.table("gap_map_scores").upsert(payload, on_conflict="axis_id").execute()
            except Exception:
                payload.pop("lc_evidence", None)
                logger.debug("gap_map_scores upsert: lc_evidence 제외 재시도. axis_id=%s", payload.get("axis_id"))
                db.table("gap_map_scores").upsert(payload, on_conflict="axis_id").execute()
        return True
    except Exception as e:
        logger.debug("gap_map_scores upsert_bulk 전체 실패, lc_evidence 제외 일괄 재시도. %s", e)
        try:
            db = get_db()
            for p in payloads:
                p_no_ev = {k: v for k, v in p.items() if k != "lc_evidence"}
                db.table("gap_map_scores").upsert(p_no_ev, on_conflict="axis_id").execute()
            return True
        except Exception:
            return False


def upsert_gi_components_bulk(rows: List[dict]) -> bool:
    """국제 데이터: 축별 Freq/Rec/Inc/Sys 일괄 upsert. rows = [{"axis_id","freq","rec","inc","sys","source_doc"}, ...]."""
    try:
        from app.core.database import get_db
        db = get_db()
        for row in rows:
            axis_id = row.get("axis_id")
            if axis_id not in RISK_AXIS_IDS:
                continue
            freq = max(0.0, min(1.0, float(row.get("freq", 0))))
            rec = max(0.0, min(1.0, float(row.get("rec", 0))))
            inc = max(0.0, min(1.0, float(row.get("inc", 0))))
            sys = max(0.0, min(1.0, float(row.get("sys", 0))))
            source_doc = row.get("source_doc")
            db.table("gap_map_gi_components").upsert(
                {"axis_id": axis_id, "freq": freq, "rec": rec, "inc": inc, "sys": sys, "source_doc": source_doc},
                on_conflict="axis_id",
            ).execute()
        return True
    except Exception:
        return False
