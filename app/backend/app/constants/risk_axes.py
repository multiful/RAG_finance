"""
스테이블코인·STO 결합 환경용 10대 리스크 축 (KAI 문서 page_9 기준).

- 적용 범위: 스테이블코인과 토큰증권(STO)이 결합된 환경에서의 리스크를 축별로 정의.
- GI (Global Importance, 0~1): 국제기구(FSB·BIS·IMF 등) 문헌·권고에서 해당 축을 얼마나 중요하게 다루는지.
  공식: GI = 0.3·Freq + 0.3·Rec + 0.2·Inc + 0.2·Sys (gap_map_gi_components 사용 시).
- LC (Local Coverage, 0~1): 우리나라 법제가 해당 리스크 축을 얼마나 직접 규율하는지. 0=미포섭, 1=직접 규율.
- Gap = GI × (1 - LC): 국제적 중요도에 비해 국내가 미흡한 정도. Gap이 크면 = 국제 기준 대비 우리나라 규제 보완이 필요한 축.
- 위험 판단: Gap≥0.5 고위험(우리나라 보완 필요), 0.3≤Gap<0.5 중위험, Gap<0.3 저위험.
- 초기 데이터(page_18): R3 0.64, R2 0.56, R5 0.54 등. 실제값은 gap_map_scores/gi_components DB 우선.
"""
from typing import List, Dict, Any

# 10대 리스크 축 ID 및 한글명 (KAI page_9)
RISK_AXIS_IDS = [
    "R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9", "R10"
]

RISK_AXIS_NAMES: Dict[str, str] = {
    "R1": "런·유동성 연쇄 리스크",
    "R2": "준비자산–담보 상관 리스크",
    "R3": "오라클·데이터 무결성 리스크",
    "R4": "스마트컨트랙트 실패·연쇄 부도 리스크",
    "R5": "규제 경계·차익거래 리스크",
    "R6": "역외·외환·자본유출 리스크",
    "R7": "투자자보호·공시 리스크",
    "R8": "자금세탁·불법사용 리스크 (AML/CFT)",
    "R9": "거버넌스·집중도 리스크",
    "R10": "상호운용성·Atomic Swap 실패 리스크",
}

# 축별 간단 설명 (대시보드/툴팁용)
RISK_AXIS_DESCRIPTIONS: Dict[str, str] = {
    "R1": "스테이블코인 런 또는 유동성 부족에 따른 연쇄 리스크",
    "R2": "준비자산과 담보의 상관관계로 인한 가치 변동 리스크",
    "R3": "오라클·외부 데이터 조작·무결성 훼손 리스크",
    "R4": "스마트컨트랙트 결함·연쇄 부도 리스크",
    "R5": "규제 경계·관할 불명확성·차익거래 리스크",
    "R6": "역외 이전·외환·자본유출 관련 리스크",
    "R7": "투자자 보호·공시 미흡 리스크",
    "R8": "자금세탁·테러자금조달(AML/CFT) 리스크",
    "R9": "거버넌스·시장 집중도 리스크",
    "R10": "상호운용성·원자적 스왑 실패 리스크",
}

# 초기 GI(Global Impact), LC(Legal Coverage) — 논문·슬라이드 기준. Gap은 서비스에서 계산.
# LC: 0.0 = 직접 규율, 0.5 = 간접·일반 원칙, 1.0 = 미포섭
RISK_AXIS_INITIAL_GI_LC: List[Dict[str, Any]] = [
    {"axis_id": "R1", "gi": 0.50, "lc": 0.5},
    {"axis_id": "R2", "gi": 0.56, "lc": 0.0},
    {"axis_id": "R3", "gi": 0.64, "lc": 0.0},
    {"axis_id": "R4", "gi": 0.50, "lc": 0.0},
    {"axis_id": "R5", "gi": 0.54, "lc": 0.0},
    {"axis_id": "R6", "gi": 0.45, "lc": 0.5},
    {"axis_id": "R7", "gi": 0.40, "lc": 0.5},
    {"axis_id": "R8", "gi": 0.55, "lc": 0.5},
    {"axis_id": "R9", "gi": 0.48, "lc": 0.0},
    {"axis_id": "R10", "gi": 0.42, "lc": 0.5},
]


def get_risk_axis_display_name(axis_id: str) -> str:
    """축 ID에 대한 한글 표기명 반환."""
    return RISK_AXIS_NAMES.get(axis_id, axis_id)


def get_risk_axis_description(axis_id: str) -> str:
    """축 ID에 대한 설명 반환."""
    return RISK_AXIS_DESCRIPTIONS.get(axis_id, "")
