"""샌드박스 시나리오 시뮬레이션 API (방안 B). 동일 입력 시 Redis 캐시 반환."""
import hashlib
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional

from app.services.sandbox_simulator_service import run_sandbox_simulation
from app.core.cache_helper import cache_get, cache_set, CACHE_TTL_SANDBOX_SIMULATE

router = APIRouter(prefix="/sandbox", tags=["Sandbox"])


class ChecklistWeaknessItem(BaseModel):
    question_id: str
    question_ko: Optional[str] = None
    response: str  # no | partial


class SandboxSimulateRequest(BaseModel):
    blind_spot_axes: Optional[List[str]] = Field(default=None, description="Gap Map 축 ID (미제공 시 상위 5개 사용)")
    checklist_weaknesses: Optional[List[ChecklistWeaknessItem]] = Field(default=None, description="체크리스트 약점(아니오/부분 응답)")


def _sandbox_cache_key(body: SandboxSimulateRequest) -> str:
    """요청 body 기반 캐시 키 (동일 입력 시 재사용)."""
    payload = {
        "blind_spot_axes": sorted(body.blind_spot_axes) if body.blind_spot_axes else None,
        "checklist_weaknesses": [
            {"question_id": w.question_id, "question_ko": w.question_ko or "", "response": w.response}
            for w in (body.checklist_weaknesses or [])
        ],
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    h = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"sandbox:simulate:{h}"


@router.post("/simulate")
async def api_sandbox_simulate(body: SandboxSimulateRequest):
    """
    Gap Map 사각지대 + 체크리스트 약점 기반 샌드박스 시나리오 시뮬레이션.
    RAG(국제·국내 문서) 참조 후 LLM이 검토 포인트·완화 가능성·권고를 생성합니다.
    동일 입력 시 10분간 Redis 캐시 결과 반환.
    """
    try:
        cache_key = _sandbox_cache_key(body)
        cached = cache_get(cache_key)
        if cached is not None and isinstance(cached, dict):
            return cached

        weaknesses = None
        if body.checklist_weaknesses:
            weaknesses = [
                {"question_id": w.question_id, "question_ko": w.question_ko or "", "response": w.response}
                for w in body.checklist_weaknesses
            ]
        result = await run_sandbox_simulation(
            blind_spot_axes=body.blind_spot_axes,
            checklist_weaknesses=weaknesses,
        )
        cache_set(cache_key, result, CACHE_TTL_SANDBOX_SIMULATE)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
