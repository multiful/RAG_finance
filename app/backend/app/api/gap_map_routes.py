"""Risk–Policy Gap Map API (KAI 문서 기반)."""
import json
import logging
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Query, Path, HTTPException

from app.core.config import settings
from app.core.database import get_db
from app.core.cache_helper import cache_get, cache_set, CACHE_TTL_GAP_MAP
from app.services.gap_map_service import (
    get_gap_map,
    get_gap_map_fallback,
    get_top_blind_spots,
    get_heatmap_data,
    update_scores,
    upsert_scores_bulk,
    upsert_gi_components_bulk,
    get_lc_evidence_all,
    _load_gi_components_from_db,
    _compute_gi_from_components,
)
from app.constants.risk_axes import RISK_AXIS_IDS
from app.models.gap_map_schemas import (
    GapMapResponse,
    TopBlindSpotsResponse,
    GapMapHeatmapRow,
    GapMapScoreUpdate,
    GapMapScoresBulkUpdate,
    GiComponentItem,
    GiComponentsBulkUpdate,
    LCEvidenceResponse,
    LCEvidenceItem,
)

router = APIRouter(prefix="/gap-map", tags=["Gap Map"])


@router.get("", response_model=GapMapResponse)
async def api_get_gap_map():
    """전체 Gap Map (리스크 축별 GI, LC, Gap). Redis 5분 캐시."""
    cache_key = "gap_map:full"
    cached = cache_get(cache_key)
    if cached is not None and isinstance(cached, dict) and "items" in cached:
        try:
            from app.models.gap_map_schemas import RiskAxisScore
            items = [RiskAxisScore(**x) for x in cached["items"]]
            return GapMapResponse(items=items, formula=cached.get("formula", "Gap = GI × (1 - LC)"))
        except Exception:
            pass
    try:
        items = get_gap_map()
        out = GapMapResponse(items=items, formula="Gap = GI × (1 - LC)")
        cache_set(cache_key, {"items": [x.model_dump() for x in items], "formula": out.formula}, CACHE_TTL_GAP_MAP)
        return out
    except Exception as e:
        logging.error(f"Error in api_get_gap_map: {e}")
        return GapMapResponse(items=get_gap_map_fallback(), formula="Gap = GI × (1 - LC)")


@router.get("/top-blind-spots", response_model=TopBlindSpotsResponse)
async def api_get_top_blind_spots(limit: int = Query(3, ge=1, le=10)):
    """상위 N대 사각지대 (Gap 높은 순). Redis 5분 캐시."""
    cache_key = f"gap_map:top:{limit}"
    cached = cache_get(cache_key)
    if cached is not None and isinstance(cached, dict) and "items" in cached:
        try:
            from app.models.gap_map_schemas import BlindSpotItem
            items = [BlindSpotItem(**x) for x in cached["items"]]
            return TopBlindSpotsResponse(items=items, formula=cached.get("formula", "Gap = GI × (1 - LC)"))
        except Exception:
            pass
    try:
        items = get_top_blind_spots(limit=limit)
        out = TopBlindSpotsResponse(items=items, formula="Gap = GI × (1 - LC)")
        cache_set(cache_key, {"items": [x.model_dump() for x in items], "formula": out.formula}, CACHE_TTL_GAP_MAP)
        return out
    except Exception as e:
        logging.error(f"Error in api_get_top_blind_spots: {e}")
        full = get_gap_map_fallback()
        sorted_by_gap = sorted(full, key=lambda x: x.gap, reverse=True)
        from app.models.gap_map_schemas import BlindSpotItem
        from app.constants.risk_axes import RISK_AXIS_DESCRIPTIONS
        items = [
            BlindSpotItem(rank=i + 1, axis_id=x.axis_id, name_ko=x.name_ko, gap=x.gap, description=RISK_AXIS_DESCRIPTIONS.get(x.axis_id, ""))
            for i, x in enumerate(sorted_by_gap[:limit])
        ]
        return TopBlindSpotsResponse(items=items, formula="Gap = GI × (1 - LC)")


@router.get("/heatmap", response_model=list[GapMapHeatmapRow])
async def api_get_gap_map_heatmap():
    """Heatmap용 2차원 데이터 (축 x GI/LC/Gap)."""
    try:
        return get_heatmap_data()
    except Exception as e:
        logging.error(f"Error in api_get_gap_map_heatmap: {e}")
        fallback = get_gap_map_fallback()
        return [GapMapHeatmapRow(axis_id=s.axis_id, name_ko=s.name_ko, gi=s.gi, lc=s.lc, gap=s.gap) for s in fallback]


@router.get("/lc-evidence", response_model=LCEvidenceResponse)
async def api_get_lc_evidence():
    """LC 값 근거(법령·조항·출처) 전체 조회 — RAG 기반 RCC 근거 보기."""
    items = get_lc_evidence_all()
    return LCEvidenceResponse(
        items=[LCEvidenceItem(
            axis_id=x["axis_id"],
            name_ko=x["name_ko"],
            lc=x["lc"],
            lc_evidence=x.get("lc_evidence") or "",
            source_or_note=x.get("source_or_note") or "",
        ) for x in items]
    )


@router.get("/lc-evidence/export")
async def api_export_lc_evidence(format: str = Query("json", regex="^(json|csv)$")):
    """LC 근거 내보내기 (JSON 또는 CSV)."""
    items = get_lc_evidence_all()
    if format == "csv":
        import io
        import csv
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["axis_id", "name_ko", "lc", "lc_evidence", "source_or_note"])
        for x in items:
            w.writerow([
                x["axis_id"],
                x["name_ko"],
                x["lc"],
                (x.get("lc_evidence") or "").replace("\n", " "),
                (x.get("source_or_note") or "").replace("\n", " "),
            ])
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(
            buf.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=gap_map_lc_evidence.csv"},
        )
    return {"items": items, "formula": "LC: 0=미포섭, 0.5=간접, 1=직접 규율"}


@router.patch("/scores/{axis_id}")
async def api_patch_gap_map_scores(
    axis_id: str = Path(..., pattern="^R(1|2|3|4|5|6|7|8|9|10)$"),
    body: GapMapScoreUpdate = ...,
):
    """관리자: 단일 축 GI/LC/LC근거 수정. gi, lc, source_or_note, lc_evidence 중 전달된 필드만 갱신."""
    if body.gi is not None or body.lc is not None or body.source_or_note is not None or body.lc_evidence is not None:
        update_scores(axis_id, gi=body.gi, lc=body.lc, source_or_note=body.source_or_note, lc_evidence=body.lc_evidence)
        return {"ok": True, "axis_id": axis_id}
    raise HTTPException(status_code=400, detail="gi, lc, source_or_note, lc_evidence 중 하나 이상 필요")


@router.put("/scores")
async def api_put_gap_map_scores(body: GapMapScoresBulkUpdate = ...):
    """관리자: 여러 축 일괄 GI/LC/LC근거 수정. DB upsert."""
    upsert_scores_bulk([s.model_dump() for s in body.scores])
    return {"ok": True, "updated": len(body.scores)}


@router.get("/domestic-international-comparison")
async def api_get_domestic_international_comparison(days: int = Query(90, ge=7, le=365)):
    """
    국내(금융위·금감원) vs 국제(FSB·BIS) 문서 건수 비교.
    Gap Map에서 국제 기준 대비 국내 규제 현황 대조용.
    """
    try:
        db = get_db()
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        all_sources = db.table("sources").select("source_id, fid, name").execute()
        domestic_ids = []
        international_ids = []
        domestic_names = []
        international_names = []
        for s in (all_sources.data or []):
            fid = s.get("fid") or ""
            if fid in settings.FSC_RSS_FIDS or (fid and fid.upper() == "FSS"):
                domestic_ids.append(s["source_id"])
                domestic_names.append(s.get("name") or fid)
            elif fid:
                international_ids.append(s["source_id"])
                international_names.append(s.get("name") or fid)
        domestic_count = 0
        if domestic_ids:
            r = db.table("documents").select("*", count="exact").in_(
                "source_id", domestic_ids
            ).gte("published_at", since).execute()
            domestic_count = (r.count if hasattr(r, "count") else 0) or 0
        international_count = 0
        if international_ids:
            r = db.table("documents").select("*", count="exact").in_(
                "source_id", international_ids
            ).gte("published_at", since).execute()
            international_count = (r.count if hasattr(r, "count") else 0) or 0
        return {
            "period_days": days,
            "domestic": {
                "document_count": domestic_count,
                "sources": domestic_names,
            },
            "international": {
                "document_count": international_count,
                "sources": international_names,
            },
            "summary": f"국내 {domestic_count}건, 국제 {international_count}건 (최근 {days}일)",
        }
    except Exception as e:
        logging.error(f"Error in domestic-international-comparison: {e}")
        return {
            "period_days": days,
            "domestic": {"document_count": 0, "sources": []},
            "international": {"document_count": 0, "sources": []},
            "summary": "국내 0건, 국제 0건",
        }


@router.get("/gi-components")
async def api_get_gi_components():
    """관리자: 국제 데이터(GI 세부 Freq/Rec/Inc/Sys) 조회. gap_map_gi_components 테이블."""
    try:
        data = _load_gi_components_from_db()
        if not data:
            return {"items": []}
        items = [
            {
                "axis_id": aid,
                "freq": c["freq"], "rec": c["rec"], "inc": c["inc"], "sys": c["sys"],
                "source_doc": c.get("source_doc"),
                "gi_computed": _compute_gi_from_components(c["freq"], c["rec"], c["inc"], c["sys"]),
            }
            for aid, c in data.items()
        ]
        return {"items": items}
    except Exception as e:
        logging.error(f"Error in api_get_gi_components: {e}")
        return {"items": []}


@router.put("/gi-components")
async def api_put_gi_components(body: GiComponentsBulkUpdate = ...):
    """관리자: 국제 데이터(Freq/Rec/Inc/Sys) 일괄 입력. 있으면 해당 축 GI는 공식으로 자동 계산됨."""
    upsert_gi_components_bulk([c.model_dump() for c in body.components])
    return {"ok": True, "updated": len(body.components)}
