"""
KAI(핵심 성과 지표) 목표치 — competition 문서 page_29 (파일럿 검증 계획) 기준.

스테이블코인–STO 결합 Risk–Policy Gap Map 및 Sandbox Framework 논문에서 제시한
파일럿 검증 목표. 실증 가능한 솔루션 입증용.
"""
from typing import Dict, Any

# 목표 지표 (page_29 핵심 성과 지표)
KAI_HALLUCINATION_RATE_MAX_PCT = 5.0   # Hallucination Rate < 5%
KAI_ACCURACY_MIN_PCT = 95.0            # 정확도 > 95%
KAI_RESPONSE_TIME_MAX_SEC = 3.0         # 응답 시간 < 3초
KAI_USER_SATISFACTION_MIN = 4.0        # 사용자 만족도 > 4.0 (5점 척도 가정)

# 설명 (API/대시보드 노출용)
KAI_TARGETS: Dict[str, Dict[str, Any]] = {
    "hallucination_rate_pct": {
        "target_value": KAI_HALLUCINATION_RATE_MAX_PCT,
        "operator": "lt",  # less than
        "unit": "%",
        "label_ko": "Hallucination Rate",
        "description_ko": "존재하지 않는 법령 인용 또는 잘못된 정보 생성 비율. 5% 미만 목표.",
        "source": "page_29 파일럿 검증 계획",
    },
    "accuracy_pct": {
        "target_value": KAI_ACCURACY_MIN_PCT,
        "operator": "gt",  # greater than
        "unit": "%",
        "label_ko": "정확도",
        "description_ko": "올바른 법령 조문 인용 비율 및 해석의 정확성. 95% 이상 목표.",
        "source": "page_29 파일럿 검증 계획",
    },
    "response_time_sec": {
        "target_value": KAI_RESPONSE_TIME_MAX_SEC,
        "operator": "lt",
        "unit": "초",
        "label_ko": "응답 시간",
        "description_ko": "질의 응답 지연 시간. 3초 미만 목표.",
        "source": "page_29 파일럿 검증 계획",
    },
    "user_satisfaction": {
        "target_value": KAI_USER_SATISFACTION_MIN,
        "operator": "gt",
        "unit": "점",
        "label_ko": "사용자 만족도",
        "description_ko": "5점 척도 사용자 만족도. 4.0 이상 목표.",
        "source": "page_29 파일럿 검증 계획",
    },
}


def check_kai_pass(current: float, key: str) -> bool:
    """현재값이 KAI 목표를 충족하는지 판단."""
    if key not in KAI_TARGETS:
        return False
    t = KAI_TARGETS[key]
    op = t.get("operator")
    target = t["target_value"]
    if op == "lt":
        return current < target
    if op == "gt":
        return current > target
    return False


def get_kai_targets_summary() -> Dict[str, Any]:
    """KAI 목표 요약 (API 응답용)."""
    return {
        "framework": "스테이블코인–STO 결합 Risk–Policy Gap Map 및 Sandbox Framework",
        "source_slide": "page_29 파일럿 검증 계획 — 핵심 성과 지표",
        "targets": KAI_TARGETS,
        "numeric_limits": {
            "hallucination_rate_max_pct": KAI_HALLUCINATION_RATE_MAX_PCT,
            "accuracy_min_pct": KAI_ACCURACY_MIN_PCT,
            "response_time_max_sec": KAI_RESPONSE_TIME_MAX_SEC,
            "user_satisfaction_min": KAI_USER_SATISFACTION_MIN,
        },
    }
