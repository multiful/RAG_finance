"""
Sandbox Risk-Based Checklist 서비스 (KAI page_20, page_22).

- get_checklist_template(): KAI 기반 실무 질문 목록
- submit_self_assessment(answers): 자가진단 응답 저장 (메모리)
- get_gap_remediation_suggestions(answers): 아니오/부분 응답 → Gap 보완 제안
"""
from typing import List, Dict, Any, Optional

from app.constants.sandbox_checklist_template import (
    DESIGN_PRINCIPLES,
    CHECKLIST_QUESTIONS,
    ANSWER_OPTIONS,
    GROUP_LABELS,
    CHECKLIST_GROUP_R3R4,
    CHECKLIST_GROUP_R5R9,
)
from app.services.gap_map_service import get_top_blind_spots


# 인메모리 저장 (1차 구현). 추후 DB 연동 시 Supabase 테이블로 대체 가능.
_submissions: List[Dict[str, Any]] = []


def get_checklist_template() -> Dict[str, Any]:
    """KAI 기반 Sandbox 체크리스트 템플릿 반환."""
    return {
        "design_principles": DESIGN_PRINCIPLES,
        "groups": [
            {"id": CHECKLIST_GROUP_R3R4, "label": GROUP_LABELS[CHECKLIST_GROUP_R3R4]},
            {"id": CHECKLIST_GROUP_R5R9, "label": GROUP_LABELS[CHECKLIST_GROUP_R5R9]},
        ],
        "questions": CHECKLIST_QUESTIONS,
        "answer_options": ANSWER_OPTIONS,
    }


def submit_self_assessment(answers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    자가진단 응답 저장.
    answers: [ {"question_id": "q_r3r4_1", "value": "yes"|"no"|"partial"}, ... ]
    """
    from datetime import datetime, timezone

    record = {
        "submission_id": f"sub_{len(_submissions) + 1}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "answers": answers,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }
    _submissions.append(record)
    return {
        "submission_id": record["submission_id"],
        "message": "자가진단이 제출되었습니다.",
        "submitted_at": record["submitted_at"],
    }


def get_gap_remediation_suggestions(answers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    '아니오'/'부분적' 응답을 높은 Gap 축과 연결해 보완 계획 제안.
    KAI: "아니오/부분적 응답 영역은 자동적으로 높은 Gap Score와 연결되어 집중 관리 대상으로 식별"
    """
    # question_id -> axis_ids 매핑
    q_to_axes: Dict[str, List[str]] = {
        q["question_id"]: q["axis_ids"] for q in CHECKLIST_QUESTIONS
    }
    # Gap 상위 축 (R3, R2, R5 등) 참조
    blind_spots = get_top_blind_spots(limit=5)
    axis_gap_rank = {item.axis_id: item.gap for item in blind_spots}

    suggestions: List[Dict[str, Any]] = []
    seen_axes: set = set()

    for a in answers:
        question_id = a.get("question_id")
        value = a.get("value", "").lower()
        if value not in ("no", "partial"):
            continue
        axes = q_to_axes.get(question_id, [])
        q_info = next((q for q in CHECKLIST_QUESTIONS if q["question_id"] == question_id), None)
        q_label = q_info["question_ko"] if q_info else question_id
        for axis_id in axes:
            if axis_id in seen_axes:
                continue
            seen_axes.add(axis_id)
            gap_val = axis_gap_rank.get(axis_id, 0)
            suggestions.append({
                "question_id": question_id,
                "axis_id": axis_id,
                "question_ko": q_label,
                "response": "아니오" if value == "no" else "부분적",
                "gap_score": round(gap_val, 2),
                "suggestion_ko": _remediation_message(axis_id, value),
            })

    # Gap 높은 순 정렬
    suggestions.sort(key=lambda x: x["gap_score"], reverse=True)
    return suggestions


def _remediation_message(axis_id: str, response: str) -> str:
    """축별 보완 권고 문구 (규칙 기반)."""
    messages = {
        "R3": "오라클·데이터 무결성: 멀티 오라클 도입 및 조작 탐지·Fallback 절차를 수립하세요.",
        "R4": "스마트컨트랙트: 긴급 중단·롤백 정책 및 정기 외부 감사를 도입하세요.",
        "R5": "규제 경계: 참여자별 R&R 및 금융당국 보고 체계를 명확히 하세요.",
        "R9": "거버넌스: 분쟁 해결 절차 및 규제 사각지대 매핑을 정비하세요.",
    }
    base = messages.get(axis_id, f"{axis_id} 리스크 축에 대한 보완 계획을 수립하세요.")
    if response == "no":
        return base
    return base.replace("수립하세요.", "보강하세요.").replace("도입하세요.", "강화하세요.")
