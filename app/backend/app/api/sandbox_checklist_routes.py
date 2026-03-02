"""Sandbox Risk-Based Checklist API (KAI page_20, page_22)."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
from typing import List

from app.services.sandbox_checklist_service import (
    get_checklist_template,
    submit_self_assessment,
    get_gap_remediation_suggestions,
)

router = APIRouter(prefix="/sandbox/checklist", tags=["Sandbox Checklist"])


class AnswerItem(BaseModel):
    question_id: str
    value: str  # yes | no | partial

    @field_validator("value")
    @classmethod
    def value_one_of(cls, v: str) -> str:
        if v not in ("yes", "no", "partial"):
            raise ValueError("value must be one of: yes, no, partial")
        return v


class SubmitRequest(BaseModel):
    answers: List[AnswerItem] = Field(default_factory=list, description="질문별 응답", min_length=1)


@router.get("", response_model=dict)
async def api_get_checklist_template():
    """Sandbox 체크리스트 템플릿 조회 (설계 원칙 + 질문 목록)."""
    return get_checklist_template()


@router.post("/submit", response_model=dict)
async def api_submit_self_assessment(body: SubmitRequest):
    """자가진단 제출."""
    answers = [{"question_id": a.question_id, "value": a.value} for a in body.answers]
    return submit_self_assessment(answers)


@router.post("/remediation", response_model=List[dict])
async def api_get_remediation(body: SubmitRequest):
    """제출된 응답 기반 Gap 보완 제안 (아니오/부분적 → 보완 문구)."""
    if not body.answers:
        raise HTTPException(status_code=400, detail="answers 필수 (최소 1건)")
    answers = [{"question_id": a.question_id, "value": a.value} for a in body.answers]
    return get_gap_remediation_suggestions(answers)
