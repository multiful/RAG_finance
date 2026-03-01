"""
KAI 문서(page_20, page_22) 기반 Sandbox Risk-Based Checklist 템플릿.

- 설계 원칙: 증분적 결합 관점, 국제 기준 호환성, 정량적 측정 가능성
- 실무 진단: R3·R4 기술 무결성, R5·R9 책임 소재·분쟁 해결
- 선택지: yes / no / partial
"""
from typing import List, Dict, Any

CHECKLIST_GROUP_R3R4 = "technical_integrity"  # R3·R4 기술적 무결성 및 복원력
CHECKLIST_GROUP_R5R9 = "liability_governance"  # R5·R9 책임 소재 및 분쟁 해결

# 설계 원칙 3개 (page_20)
DESIGN_PRINCIPLES: List[Dict[str, str]] = [
    {
        "id": "incremental",
        "title": "증분적 결합 관점",
        "description": "스테이블코인·STO 개별 리스크와 결합 구조 특유의 상호작용을 단계별로 분리하여 식별",
        "icon_hint": "layer-group",
    },
    {
        "id": "international",
        "title": "국제 기준 호환성",
        "description": "FSB GSC 10대 권고 및 IMF-FSB Synthesis Paper 등 글로벌 규제 스탠다드와 매핑",
        "icon_hint": "globe",
    },
    {
        "id": "quantitative",
        "title": "정량적 측정 가능성",
        "description": "단순 서술형을 넘어 이벤트 빈도, 손실률, HHI 등 데이터 기반 지표와 연계",
        "icon_hint": "chart-line",
    },
]

# 실무 진단 항목: 그룹별 질문 (page_22)
# 각 항목: question_id, axis_ids(연관 리스크 축), question_ko, description_ko
CHECKLIST_QUESTIONS: List[Dict[str, Any]] = [
    # R3·R4: 기술적 무결성 및 복원력
    {
        "question_id": "q_r3r4_1",
        "group_id": CHECKLIST_GROUP_R3R4,
        "axis_ids": ["R3", "R4"],
        "question_ko": "오라클 및 데이터 가용성",
        "description_ko": "이중화·멀티 오라클 체계, 데이터 조작 탐지 알림 및 Fallback(대체) 메커니즘 구축 여부",
    },
    {
        "question_id": "q_r3r4_2",
        "group_id": CHECKLIST_GROUP_R3R4,
        "axis_ids": ["R3", "R4"],
        "question_ko": "스마트컨트랙트 제어 권한",
        "description_ko": "비정상 거래 시 긴급 중단(Emergency Halt) 및 롤백 정책, 멀티시그(Multi-sig) 거버넌스 적용 여부",
    },
    {
        "question_id": "q_r3r4_3",
        "group_id": CHECKLIST_GROUP_R3R4,
        "axis_ids": ["R3", "R4"],
        "question_ko": "상시 보안 검증 체계",
        "description_ko": "정기적 외부 감사(Audit) 수행 및 버그바운티 프로그램 운영을 통한 취약점 선제적 관리",
    },
    # R5·R9: 책임 소재 및 분쟁 해결
    {
        "question_id": "q_r5r9_1",
        "group_id": CHECKLIST_GROUP_R5R9,
        "axis_ids": ["R5", "R9"],
        "question_ko": "참여자 간 역할 및 책임(R&R)",
        "description_ko": "발행사, 플랫폼, 수탁기관, 오라클 제공자 간 사고 발생 시 손실 분담 비율 및 배상 책임 명문화",
    },
    {
        "question_id": "q_r5r9_2",
        "group_id": CHECKLIST_GROUP_R5R9,
        "axis_ids": ["R5", "R9"],
        "question_ko": "분쟁 해결 절차의 구체성",
        "description_ko": "온체인 사고 및 데이터 불일치 시 오프라인 구제 절차 연계, 분쟁 해결을 위한 전담 창구 및 프로세스 보유",
    },
    {
        "question_id": "q_r5r9_3",
        "group_id": CHECKLIST_GROUP_R5R9,
        "axis_ids": ["R5", "R9"],
        "question_ko": "규제 대응 및 보고 체계",
        "description_ko": "금융당국(FSC/FSS) 보고 가이드라인 준수, 법률 체계(전자금융/자본시장/가상자산) 간 사각지대 매핑",
    },
]

ANSWER_OPTIONS = [
    {"value": "yes", "label_ko": "예"},
    {"value": "no", "label_ko": "아니오"},
    {"value": "partial", "label_ko": "부분적"},
]

GROUP_LABELS: Dict[str, str] = {
    CHECKLIST_GROUP_R3R4: "기술적 무결성 및 복원력 (R3·R4)",
    CHECKLIST_GROUP_R5R9: "책임 소재 및 분쟁 해결 (R5·R9)",
}
