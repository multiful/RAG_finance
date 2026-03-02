"""
Local Coverage (LC) 라벨링 기준 및 분석 대상 법령 (KAI 문서 page_16).

- LC 0.0~1.0: 한국 법제의 리스크 포섭 수준 정량화.
- RAG 기반 RCC(Regulatory Compliance Checking) 개념으로 법령 텍스트 내 리스크 키워드·감독 수단 매핑.
"""
from typing import List, Dict, Any

# LC 산출 기준 (page_16)
LC_LABELING_CRITERIA: List[Dict[str, Any]] = [
    {
        "score": 1.0,
        "label_ko": "직접적·구체적 규율",
        "description_ko": "해당 리스크를 핵심 요소로 명시하고, 정의·규제 도구·감독 수단이 구체적인 법문에 명시된 경우",
    },
    {
        "score": 0.5,
        "label_ko": "간접적·일반 원칙 포섭",
        "description_ko": "인접 리스크나 일반 원칙 수준으로 포괄하나, 결합 구조의 특수성이나 기술적 메커니즘을 다루지 않는 경우",
    },
    {
        "score": 0.0,
        "label_ko": "규율 근거 부재",
        "description_ko": "해당 리스크에 대한 직접적인 언급이나 포섭할 수 있는 법적 근거가 사실상 존재하지 않는 경우",
    },
]

# 분석 대상 법령 및 가이드라인 (page_16)
TARGET_LEGISLATION: List[Dict[str, str]] = [
    {"name_ko": "가상자산이용자보호법", "description_ko": "이용자 자산 보호 및 불공정거래 규율 중심"},
    {"name_ko": "토큰증권(STO) 정비방안", "description_ko": "발행·유통 분리 및 분산원장 전자등록 체계"},
    {"name_ko": "전자금융거래법", "description_ko": "지급결제 수단 및 전자금융업자 운영 리스크 관리"},
    {"name_ko": "외국환거래법", "description_ko": "국경 간 자본 이동 및 외환 거래 건전성 규제"},
]

NOTE_LEGISLATION = "관련 시행령, 감독규정 및 금융당국 배포 가이드라인 포함"
NOTE_METHODOLOGY = (
    "본 연구는 RAG 기반 Regulatory Compliance Checking (RCC) 개념을 차용하여, "
    "법령 텍스트 내 리스크 관련 키워드와 감독 수단의 존재 여부를 매핑하여 객관성을 확보함."
)


def get_lc_labeling_meta() -> Dict[str, Any]:
    """API용: LC 라벨링 기준 + 대상 법령 요약."""
    return {
        "source": "page_16 Local Coverage (LC) 라벨링 기준 및 대상 법령",
        "criteria": LC_LABELING_CRITERIA,
        "target_legislation": TARGET_LEGISLATION,
        "note_legislation": NOTE_LEGISLATION,
        "note_methodology": NOTE_METHODOLOGY,
    }
