"""Golden Dataset for RAG Evaluation.

Contains 50+ financial policy questions with ground truth answers,
difficulty levels, and expected retrieval sources for benchmark testing.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class QuestionDifficulty(str, Enum):
    """Question difficulty levels."""
    FACTUAL = "factual"         # Simple fact lookup
    REASONING = "reasoning"     # Requires inference
    COMPARATIVE = "comparative" # Compare policies/versions
    MULTI_HOP = "multi_hop"     # Requires multiple documents


class IndustryFocus(str, Enum):
    """Industry focus of the question."""
    INSURANCE = "INSURANCE"
    BANKING = "BANKING"
    SECURITIES = "SECURITIES"
    GENERAL = "GENERAL"


@dataclass
class GoldenQuestion:
    """A golden test question with ground truth."""
    id: str
    question: str
    difficulty: QuestionDifficulty
    industry: IndustryFocus
    expected_answer_contains: List[str]
    expected_citations_keywords: List[str]
    ground_truth_summary: str
    tags: List[str] = field(default_factory=list)


GOLDEN_DATASET: List[GoldenQuestion] = [
    # ===== 보험업 - 사실형 (10개) =====
    GoldenQuestion(
        id="INS-F-001",
        question="K-ICS(신지급여력제도)의 도입 배경은 무엇인가요?",
        difficulty=QuestionDifficulty.FACTUAL,
        industry=IndustryFocus.INSURANCE,
        expected_answer_contains=["국제기준", "IFRS17", "자본적정성", "리스크"],
        expected_citations_keywords=["K-ICS", "지급여력", "보험업감독"],
        ground_truth_summary="K-ICS는 IFRS17 도입에 맞춰 국제기준에 부합하는 리스크 기반 자본적정성 제도로, 기존 RBC 대비 리스크 측정의 정교화 및 자산-부채 평가 일관성을 강화함.",
        tags=["K-ICS", "자본규제", "IFRS17"]
    ),
    GoldenQuestion(
        id="INS-F-002",
        question="보험업감독규정상 보험사의 자산운용 한도는 어떻게 규정되어 있나요?",
        difficulty=QuestionDifficulty.FACTUAL,
        industry=IndustryFocus.INSURANCE,
        expected_answer_contains=["자산운용", "한도", "비율", "투자"],
        expected_citations_keywords=["보험업감독규정", "자산운용"],
        ground_truth_summary="보험업감독규정에 따라 총자산 대비 특정 자산군의 투자 한도가 설정되어 있으며, 주식, 부동산 등 위험자산에 대한 한도가 명시됨.",
        tags=["자산운용", "투자한도"]
    ),
    GoldenQuestion(
        id="INS-F-003",
        question="보험계약 청약철회권의 행사 기간은 얼마인가요?",
        difficulty=QuestionDifficulty.FACTUAL,
        industry=IndustryFocus.INSURANCE,
        expected_answer_contains=["15일", "30일", "청약철회", "기간"],
        expected_citations_keywords=["청약철회", "보험계약"],
        ground_truth_summary="일반적으로 보험계약일로부터 15일 이내(30일 이내 일부 예외) 청약철회가 가능하며, 이미 납입한 보험료 전액 환급됨.",
        tags=["청약철회", "소비자보호"]
    ),
    GoldenQuestion(
        id="INS-F-004",
        question="K-ICS 경과조치 기간은 얼마인가요?",
        difficulty=QuestionDifficulty.FACTUAL,
        industry=IndustryFocus.INSURANCE,
        expected_answer_contains=["경과조치", "년", "단계적"],
        expected_citations_keywords=["K-ICS", "경과조치"],
        ground_truth_summary="K-ICS 경과조치는 보험사별 준비 상황을 고려하여 단계적으로 적용되며, 자본요건의 점진적 적용이 허용됨.",
        tags=["K-ICS", "경과조치"]
    ),
    GoldenQuestion(
        id="INS-F-005",
        question="보험사 대주주 적격성 심사 기준은 무엇인가요?",
        difficulty=QuestionDifficulty.FACTUAL,
        industry=IndustryFocus.INSURANCE,
        expected_answer_contains=["대주주", "적격성", "심사", "요건"],
        expected_citations_keywords=["대주주", "적격성", "보험업법"],
        ground_truth_summary="보험업법에 따라 대주주의 재무건전성, 사회적 신용, 금융관련법 위반 여부 등을 종합 심사함.",
        tags=["대주주", "적격성심사"]
    ),
    
    # ===== 보험업 - 추론형 (5개) =====
    GoldenQuestion(
        id="INS-R-001",
        question="K-ICS 도입이 보험사 배당정책에 미치는 영향은?",
        difficulty=QuestionDifficulty.REASONING,
        industry=IndustryFocus.INSURANCE,
        expected_answer_contains=["배당", "자본", "지급여력", "제한"],
        expected_citations_keywords=["K-ICS", "배당", "자본"],
        ground_truth_summary="K-ICS 하에서 자본비율이 하락하면 배당 제한이 가능하며, 보험사는 자본확충과 배당 간 균형을 고려해야 함.",
        tags=["K-ICS", "배당정책"]
    ),
    GoldenQuestion(
        id="INS-R-002",
        question="금리 상승이 보험사 K-ICS 비율에 미치는 영향은?",
        difficulty=QuestionDifficulty.REASONING,
        industry=IndustryFocus.INSURANCE,
        expected_answer_contains=["금리", "부채", "자산", "듀레이션"],
        expected_citations_keywords=["금리", "K-ICS", "ALM"],
        ground_truth_summary="금리 상승 시 부채 감소폭이 자산 감소폭보다 크면 K-ICS 비율 개선, 반대의 경우 악화 가능.",
        tags=["금리리스크", "K-ICS"]
    ),
    GoldenQuestion(
        id="INS-R-003",
        question="저출산 고령화가 생명보험사 상품 전략에 미치는 영향은?",
        difficulty=QuestionDifficulty.REASONING,
        industry=IndustryFocus.INSURANCE,
        expected_answer_contains=["고령화", "연금", "건강", "상품"],
        expected_citations_keywords=["고령화", "보험상품", "연금"],
        ground_truth_summary="고령화에 따라 연금/건강보험 수요 증가, 사망보험 수요 감소로 상품 포트폴리오 재편 필요.",
        tags=["고령화", "상품전략"]
    ),
    GoldenQuestion(
        id="INS-R-004",
        question="IFRS17 도입이 보험사 손익 변동성에 미치는 영향은?",
        difficulty=QuestionDifficulty.REASONING,
        industry=IndustryFocus.INSURANCE,
        expected_answer_contains=["손익", "변동성", "CSM", "보험계약마진"],
        expected_citations_keywords=["IFRS17", "손익", "CSM"],
        ground_truth_summary="IFRS17 하에서 CSM 상각을 통한 이익 인식으로 손익 변동성이 완화되나, 시장금리 변동에 따른 변동성은 증가할 수 있음.",
        tags=["IFRS17", "손익변동성"]
    ),
    GoldenQuestion(
        id="INS-R-005",
        question="디지털 헬스케어 서비스가 보험 언더라이팅에 미치는 영향은?",
        difficulty=QuestionDifficulty.REASONING,
        industry=IndustryFocus.INSURANCE,
        expected_answer_contains=["디지털", "헬스케어", "언더라이팅", "리스크"],
        expected_citations_keywords=["디지털", "헬스케어", "보험"],
        ground_truth_summary="웨어러블 기기 등 디지털 헬스케어 데이터를 활용한 정밀 언더라이팅 및 맞춤형 요율 산정이 가능해짐.",
        tags=["디지털헬스케어", "언더라이팅"]
    ),
    
    # ===== 은행업 - 사실형 (10개) =====
    GoldenQuestion(
        id="BNK-F-001",
        question="DSR(총부채원리금상환비율) 규제의 적용 대상은?",
        difficulty=QuestionDifficulty.FACTUAL,
        industry=IndustryFocus.BANKING,
        expected_answer_contains=["DSR", "적용", "대출", "비율"],
        expected_citations_keywords=["DSR", "가계대출", "규제"],
        ground_truth_summary="DSR 규제는 주택담보대출 및 신용대출 등 가계대출에 적용되며, 차주의 상환능력을 종합 평가함.",
        tags=["DSR", "가계대출규제"]
    ),
    GoldenQuestion(
        id="BNK-F-002",
        question="LCR(유동성커버리지비율)의 최소 규제 비율은?",
        difficulty=QuestionDifficulty.FACTUAL,
        industry=IndustryFocus.BANKING,
        expected_answer_contains=["100%", "LCR", "유동성", "최소"],
        expected_citations_keywords=["LCR", "유동성", "규제"],
        ground_truth_summary="은행은 LCR 100% 이상을 유지해야 하며, 이는 30일간 순현금유출을 고품질 유동자산으로 커버할 수 있음을 의미함.",
        tags=["LCR", "유동성규제"]
    ),
    GoldenQuestion(
        id="BNK-F-003",
        question="지역별 LTV 규제 차등 적용 기준은?",
        difficulty=QuestionDifficulty.FACTUAL,
        industry=IndustryFocus.BANKING,
        expected_answer_contains=["LTV", "지역", "투기", "조정"],
        expected_citations_keywords=["LTV", "지역", "주택"],
        ground_truth_summary="투기지역, 투기과열지구, 조정대상지역 등 지역별로 LTV 한도가 차등 적용되며, 규제지역일수록 낮은 LTV 적용.",
        tags=["LTV", "주택담보대출"]
    ),
    GoldenQuestion(
        id="BNK-F-004",
        question="은행의 내부등급법(IRB) 승인 요건은?",
        difficulty=QuestionDifficulty.FACTUAL,
        industry=IndustryFocus.BANKING,
        expected_answer_contains=["IRB", "내부등급", "승인", "요건"],
        expected_citations_keywords=["IRB", "내부등급법", "자본"],
        ground_truth_summary="IRB 승인을 위해 최소 5년 이상의 데이터 축적, 리스크 관리 체계 구축, 감독당국 승인이 필요함.",
        tags=["IRB", "신용리스크"]
    ),
    GoldenQuestion(
        id="BNK-F-005",
        question="시스템적 중요 은행(D-SIB)의 추가 자본 요건은?",
        difficulty=QuestionDifficulty.FACTUAL,
        industry=IndustryFocus.BANKING,
        expected_answer_contains=["D-SIB", "추가", "자본", "버퍼"],
        expected_citations_keywords=["D-SIB", "시스템적중요", "자본"],
        ground_truth_summary="D-SIB로 지정된 은행은 기본 자본비율에 추가하여 추가 자본버퍼를 적립해야 함.",
        tags=["D-SIB", "자본규제"]
    ),
    GoldenQuestion(
        id="BNK-F-006",
        question="NSFR(순안정자금조달비율)의 산정 방식은?",
        difficulty=QuestionDifficulty.FACTUAL,
        industry=IndustryFocus.BANKING,
        expected_answer_contains=["NSFR", "안정", "자금", "산정"],
        expected_citations_keywords=["NSFR", "순안정자금"],
        ground_truth_summary="NSFR = 가용안정자금조달액 / 필요안정자금조달액으로 산정되며, 100% 이상 유지 필요.",
        tags=["NSFR", "유동성"]
    ),
    GoldenQuestion(
        id="BNK-F-007",
        question="은행의 대손충당금 적립 기준은?",
        difficulty=QuestionDifficulty.FACTUAL,
        industry=IndustryFocus.BANKING,
        expected_answer_contains=["대손충당금", "적립", "기준", "분류"],
        expected_citations_keywords=["대손충당금", "자산건전성"],
        ground_truth_summary="자산건전성 분류(정상~추정손실)에 따라 차등 적립률이 적용되며, IFRS9에 따른 기대신용손실 모형도 적용.",
        tags=["대손충당금", "자산건전성"]
    ),
    GoldenQuestion(
        id="BNK-F-008",
        question="은행의 예대비율 규제는?",
        difficulty=QuestionDifficulty.FACTUAL,
        industry=IndustryFocus.BANKING,
        expected_answer_contains=["예대비율", "규제", "대출", "예금"],
        expected_citations_keywords=["예대비율", "은행"],
        ground_truth_summary="예대비율(대출/예금)이 일정 수준을 초과하면 추가 안정조달 노력이 필요하며, 과거 100% 규제가 적용된 바 있음.",
        tags=["예대비율"]
    ),
    GoldenQuestion(
        id="BNK-F-009",
        question="은행 내부통제기준의 주요 내용은?",
        difficulty=QuestionDifficulty.FACTUAL,
        industry=IndustryFocus.BANKING,
        expected_answer_contains=["내부통제", "기준", "준수", "관리"],
        expected_citations_keywords=["내부통제", "은행법"],
        ground_truth_summary="은행법에 따라 내부통제기준을 마련해야 하며, 준법감시인 선임, 위험관리체계, 이해상충 방지 등이 포함됨.",
        tags=["내부통제", "준법감시"]
    ),
    GoldenQuestion(
        id="BNK-F-010",
        question="스트레스 테스트의 시나리오 구성 요소는?",
        difficulty=QuestionDifficulty.FACTUAL,
        industry=IndustryFocus.BANKING,
        expected_answer_contains=["스트레스", "테스트", "시나리오", "거시"],
        expected_citations_keywords=["스트레스테스트", "위험관리"],
        ground_truth_summary="GDP 성장률, 금리, 환율, 부동산 가격 등 거시경제 변수의 악화 시나리오를 설정하여 자본 영향 평가.",
        tags=["스트레스테스트", "위험관리"]
    ),
    
    # ===== 은행업 - 추론형 (5개) =====
    GoldenQuestion(
        id="BNK-R-001",
        question="기준금리 인상이 은행 순이자마진(NIM)에 미치는 영향은?",
        difficulty=QuestionDifficulty.REASONING,
        industry=IndustryFocus.BANKING,
        expected_answer_contains=["금리", "NIM", "마진", "예대"],
        expected_citations_keywords=["금리", "순이자마진", "은행"],
        ground_truth_summary="기준금리 인상 시 대출금리 상승이 예금금리 상승보다 빠르면 NIM 개선, 역전 시 악화 가능.",
        tags=["금리", "NIM"]
    ),
    GoldenQuestion(
        id="BNK-R-002",
        question="부동산 가격 하락이 은행 건전성에 미치는 영향은?",
        difficulty=QuestionDifficulty.REASONING,
        industry=IndustryFocus.BANKING,
        expected_answer_contains=["부동산", "담보", "LTV", "부실"],
        expected_citations_keywords=["부동산", "담보대출", "건전성"],
        ground_truth_summary="부동산 가격 하락 시 담보가치 하락으로 LTV 비율 상승, 부실채권 증가 및 충당금 적립 부담 증가 가능.",
        tags=["부동산", "자산건전성"]
    ),
    GoldenQuestion(
        id="BNK-R-003",
        question="바젤3 최종안이 은행 자본비율에 미치는 영향은?",
        difficulty=QuestionDifficulty.REASONING,
        industry=IndustryFocus.BANKING,
        expected_answer_contains=["바젤", "자본", "RWA", "영향"],
        expected_citations_keywords=["바젤3", "자본비율", "RWA"],
        ground_truth_summary="바젤3 최종안에 따른 산출기준 변경으로 RWA 증가 가능, 이에 따른 자본확충 필요성 검토 필요.",
        tags=["바젤3", "자본규제"]
    ),
    GoldenQuestion(
        id="BNK-R-004",
        question="가계부채 증가가 금융안정에 미치는 리스크는?",
        difficulty=QuestionDifficulty.REASONING,
        industry=IndustryFocus.BANKING,
        expected_answer_contains=["가계부채", "리스크", "안정", "상환"],
        expected_citations_keywords=["가계부채", "금융안정"],
        ground_truth_summary="가계부채 증가는 금리 상승 시 상환부담 증가, 소비위축, 부실화 확산으로 시스템리스크 유발 가능.",
        tags=["가계부채", "금융안정"]
    ),
    GoldenQuestion(
        id="BNK-R-005",
        question="오픈뱅킹이 은행 비즈니스 모델에 미치는 영향은?",
        difficulty=QuestionDifficulty.REASONING,
        industry=IndustryFocus.BANKING,
        expected_answer_contains=["오픈뱅킹", "API", "경쟁", "플랫폼"],
        expected_citations_keywords=["오픈뱅킹", "API", "금융혁신"],
        ground_truth_summary="오픈뱅킹으로 핀테크와의 경쟁 심화, 플랫폼 전략 필요성 증가, 수수료 수익 구조 변화 예상.",
        tags=["오픈뱅킹", "디지털금융"]
    ),
    
    # ===== 증권업 - 사실형 (10개) =====
    GoldenQuestion(
        id="SEC-F-001",
        question="금융투자업자의 영업용순자본비율 규제는?",
        difficulty=QuestionDifficulty.FACTUAL,
        industry=IndustryFocus.SECURITIES,
        expected_answer_contains=["영업용순자본", "NCR", "비율", "규제"],
        expected_citations_keywords=["영업용순자본", "NCR", "금융투자"],
        ground_truth_summary="금융투자업자는 영업용순자본비율(NCR)을 일정 수준 이상 유지해야 하며, 업종별로 차등 적용됨.",
        tags=["NCR", "자본규제"]
    ),
    GoldenQuestion(
        id="SEC-F-002",
        question="공매도 규제 현황은?",
        difficulty=QuestionDifficulty.FACTUAL,
        industry=IndustryFocus.SECURITIES,
        expected_answer_contains=["공매도", "규제", "차입", "제한"],
        expected_citations_keywords=["공매도", "자본시장법"],
        ground_truth_summary="무차입 공매도 금지, 개인투자자 차입공매도 제한 등 공매도 관련 규제가 적용되고 있음.",
        tags=["공매도", "시장규제"]
    ),
    GoldenQuestion(
        id="SEC-F-003",
        question="자본시장법상 투자권유 시 설명의무의 범위는?",
        difficulty=QuestionDifficulty.FACTUAL,
        industry=IndustryFocus.SECURITIES,
        expected_answer_contains=["설명의무", "투자권유", "위험", "중요사항"],
        expected_citations_keywords=["설명의무", "투자권유", "자본시장법"],
        ground_truth_summary="투자위험, 수수료, 원금손실 가능성 등 중요사항을 투자자가 이해할 수 있도록 설명해야 함.",
        tags=["설명의무", "투자자보호"]
    ),
    GoldenQuestion(
        id="SEC-F-004",
        question="적격기관투자자의 정의와 요건은?",
        difficulty=QuestionDifficulty.FACTUAL,
        industry=IndustryFocus.SECURITIES,
        expected_answer_contains=["적격기관투자자", "요건", "전문투자자"],
        expected_citations_keywords=["적격기관투자자", "전문투자자"],
        ground_truth_summary="일정 자산규모 이상의 기관투자자로, 전문투자자 대우를 받아 투자자보호 규제 일부 면제됨.",
        tags=["적격기관투자자", "전문투자자"]
    ),
    GoldenQuestion(
        id="SEC-F-005",
        question="금융투자상품의 위험등급 분류 기준은?",
        difficulty=QuestionDifficulty.FACTUAL,
        industry=IndustryFocus.SECURITIES,
        expected_answer_contains=["위험등급", "분류", "기준", "투자"],
        expected_citations_keywords=["위험등급", "금융투자상품"],
        ground_truth_summary="원금손실 가능성, 변동성 등을 기준으로 1~6등급으로 분류되며, 투자성향과 매칭하여 판매.",
        tags=["위험등급", "상품분류"]
    ),
    GoldenQuestion(
        id="SEC-F-006",
        question="내부자거래 규제의 대상과 처벌은?",
        difficulty=QuestionDifficulty.FACTUAL,
        industry=IndustryFocus.SECURITIES,
        expected_answer_contains=["내부자거래", "규제", "처벌", "미공개"],
        expected_citations_keywords=["내부자거래", "불공정거래"],
        ground_truth_summary="미공개 중요정보를 이용한 거래 금지, 위반 시 형사처벌 및 과징금 부과.",
        tags=["내부자거래", "불공정거래"]
    ),
    GoldenQuestion(
        id="SEC-F-007",
        question="IPO 시 수요예측 제도는?",
        difficulty=QuestionDifficulty.FACTUAL,
        industry=IndustryFocus.SECURITIES,
        expected_answer_contains=["IPO", "수요예측", "공모", "가격"],
        expected_citations_keywords=["IPO", "수요예측", "공모가"],
        ground_truth_summary="기관투자자 대상 수요예측을 통해 공모가격대를 결정하며, 적정 공모가 산정에 활용.",
        tags=["IPO", "수요예측"]
    ),
    GoldenQuestion(
        id="SEC-F-008",
        question="외국인투자자 등록제도는?",
        difficulty=QuestionDifficulty.FACTUAL,
        industry=IndustryFocus.SECURITIES,
        expected_answer_contains=["외국인", "투자자", "등록", "제도"],
        expected_citations_keywords=["외국인투자자", "등록"],
        ground_truth_summary="외국인투자자는 금융감독원에 등록 후 국내 증권시장에 투자 가능.",
        tags=["외국인투자자", "시장접근"]
    ),
    GoldenQuestion(
        id="SEC-F-009",
        question="파생상품 거래 시 개시증거금 규제는?",
        difficulty=QuestionDifficulty.FACTUAL,
        industry=IndustryFocus.SECURITIES,
        expected_answer_contains=["파생상품", "증거금", "개시", "유지"],
        expected_citations_keywords=["파생상품", "증거금"],
        ground_truth_summary="파생상품 거래 시 개시증거금 납부 필요, 유지증거금 미달 시 추가 납부 또는 청산.",
        tags=["파생상품", "증거금"]
    ),
    GoldenQuestion(
        id="SEC-F-010",
        question="증권신고서 제출 면제 기준은?",
        difficulty=QuestionDifficulty.FACTUAL,
        industry=IndustryFocus.SECURITIES,
        expected_answer_contains=["증권신고서", "면제", "기준", "공모"],
        expected_citations_keywords=["증권신고서", "공모", "면제"],
        ground_truth_summary="소액공모, 전문투자자 대상 발행 등 일정 요건 충족 시 증권신고서 제출 면제.",
        tags=["증권신고서", "공모규제"]
    ),
    
    # ===== 비교형 (10개) =====
    GoldenQuestion(
        id="CMP-001",
        question="K-ICS와 기존 RBC 제도의 주요 차이점은?",
        difficulty=QuestionDifficulty.COMPARATIVE,
        industry=IndustryFocus.INSURANCE,
        expected_answer_contains=["K-ICS", "RBC", "차이", "리스크", "평가"],
        expected_citations_keywords=["K-ICS", "RBC", "지급여력"],
        ground_truth_summary="RBC는 장부가 기반, K-ICS는 시가 기반 평가; K-ICS가 더 정교한 리스크 측정 및 국제기준 정합성 확보.",
        tags=["K-ICS", "RBC", "비교"]
    ),
    GoldenQuestion(
        id="CMP-002",
        question="DSR과 DTI 규제의 차이점은?",
        difficulty=QuestionDifficulty.COMPARATIVE,
        industry=IndustryFocus.BANKING,
        expected_answer_contains=["DSR", "DTI", "차이", "원리금", "이자"],
        expected_citations_keywords=["DSR", "DTI"],
        ground_truth_summary="DTI는 이자상환만, DSR은 원리금 전체를 소득 대비로 계산; DSR이 더 보수적인 규제.",
        tags=["DSR", "DTI", "비교"]
    ),
    GoldenQuestion(
        id="CMP-003",
        question="IFRS17과 IFRS4의 주요 차이점은?",
        difficulty=QuestionDifficulty.COMPARATIVE,
        industry=IndustryFocus.INSURANCE,
        expected_answer_contains=["IFRS17", "IFRS4", "차이", "평가", "부채"],
        expected_citations_keywords=["IFRS17", "IFRS4", "보험부채"],
        ground_truth_summary="IFRS4는 원가 기반, IFRS17은 시가 기반 부채 평가; IFRS17이 CSM 개념 도입으로 이익 인식 방식 변경.",
        tags=["IFRS17", "IFRS4", "비교"]
    ),
    GoldenQuestion(
        id="CMP-004",
        question="바젤2와 바젤3의 자본규제 차이점은?",
        difficulty=QuestionDifficulty.COMPARATIVE,
        industry=IndustryFocus.BANKING,
        expected_answer_contains=["바젤2", "바젤3", "자본", "버퍼", "유동성"],
        expected_citations_keywords=["바젤2", "바젤3", "자본규제"],
        ground_truth_summary="바젤3는 바젤2 대비 자본 질 강화, 완충자본 도입, 레버리지비율/유동성규제 신설.",
        tags=["바젤2", "바젤3", "비교"]
    ),
    GoldenQuestion(
        id="CMP-005",
        question="표준방법과 내부등급법(IRB)의 차이점은?",
        difficulty=QuestionDifficulty.COMPARATIVE,
        industry=IndustryFocus.BANKING,
        expected_answer_contains=["표준방법", "IRB", "차이", "위험가중치"],
        expected_citations_keywords=["표준방법", "IRB", "신용리스크"],
        ground_truth_summary="표준방법은 규정된 위험가중치 사용, IRB는 내부 모형으로 위험가중치 산출; IRB가 리스크 민감도 높음.",
        tags=["표준방법", "IRB", "비교"]
    ),
    GoldenQuestion(
        id="CMP-006",
        question="일반투자자와 전문투자자의 차이점은?",
        difficulty=QuestionDifficulty.COMPARATIVE,
        industry=IndustryFocus.SECURITIES,
        expected_answer_contains=["일반투자자", "전문투자자", "차이", "보호"],
        expected_citations_keywords=["일반투자자", "전문투자자"],
        ground_truth_summary="전문투자자는 금융지식과 위험감수능력이 있어 투자자보호 규제 일부 면제됨.",
        tags=["투자자분류", "비교"]
    ),
    GoldenQuestion(
        id="CMP-007",
        question="장내파생상품과 장외파생상품의 규제 차이는?",
        difficulty=QuestionDifficulty.COMPARATIVE,
        industry=IndustryFocus.SECURITIES,
        expected_answer_contains=["장내", "장외", "파생상품", "규제", "차이"],
        expected_citations_keywords=["장내파생상품", "장외파생상품"],
        ground_truth_summary="장내는 거래소 상장, 표준화; 장외는 당사자 간 맞춤형으로 중앙청산 의무화 등 별도 규제.",
        tags=["파생상품", "비교"]
    ),
    GoldenQuestion(
        id="CMP-008",
        question="국내은행과 외국은행 국내지점의 규제 차이는?",
        difficulty=QuestionDifficulty.COMPARATIVE,
        industry=IndustryFocus.BANKING,
        expected_answer_contains=["국내은행", "외국은행", "지점", "규제"],
        expected_citations_keywords=["외국은행지점", "규제"],
        ground_truth_summary="외국은행 지점은 본점 자본에 기반한 규제, 국내은행은 독립 자본규제 적용.",
        tags=["외국은행", "규제", "비교"]
    ),
    GoldenQuestion(
        id="CMP-009",
        question="금융소비자보호법과 기존 규제의 차이점은?",
        difficulty=QuestionDifficulty.COMPARATIVE,
        industry=IndustryFocus.GENERAL,
        expected_answer_contains=["금소법", "차이", "소비자", "보호"],
        expected_citations_keywords=["금융소비자보호법", "금소법"],
        ground_truth_summary="금소법은 6대 판매규제 통일, 위법계약해지권 도입, 징벌적 과징금 등 소비자보호 강화.",
        tags=["금소법", "비교"]
    ),
    GoldenQuestion(
        id="CMP-010",
        question="마이데이터와 오픈뱅킹의 차이점은?",
        difficulty=QuestionDifficulty.COMPARATIVE,
        industry=IndustryFocus.GENERAL,
        expected_answer_contains=["마이데이터", "오픈뱅킹", "차이", "정보"],
        expected_citations_keywords=["마이데이터", "오픈뱅킹"],
        ground_truth_summary="오픈뱅킹은 결제/이체 API 공유, 마이데이터는 개인신용정보 통합조회 서비스.",
        tags=["마이데이터", "오픈뱅킹", "비교"]
    ),
    
    # ===== 공통/일반 (10개) =====
    GoldenQuestion(
        id="GEN-001",
        question="금융소비자보호법의 6대 판매규제는?",
        difficulty=QuestionDifficulty.FACTUAL,
        industry=IndustryFocus.GENERAL,
        expected_answer_contains=["적합성", "적정성", "설명의무", "불공정", "부당권유", "허위"],
        expected_citations_keywords=["금융소비자보호법", "판매규제"],
        ground_truth_summary="적합성, 적정성, 설명의무, 불공정영업행위 금지, 부당권유 금지, 허위·과장광고 금지.",
        tags=["금소법", "판매규제"]
    ),
    GoldenQuestion(
        id="GEN-002",
        question="ESG 공시 의무화 로드맵은?",
        difficulty=QuestionDifficulty.FACTUAL,
        industry=IndustryFocus.GENERAL,
        expected_answer_contains=["ESG", "공시", "의무화", "단계"],
        expected_citations_keywords=["ESG", "공시", "지속가능"],
        ground_truth_summary="대형기업부터 단계적으로 ESG 공시 의무화 적용, 표준화된 공시기준 마련 예정.",
        tags=["ESG", "공시"]
    ),
    GoldenQuestion(
        id="GEN-003",
        question="가상자산이용자보호법의 주요 내용은?",
        difficulty=QuestionDifficulty.FACTUAL,
        industry=IndustryFocus.GENERAL,
        expected_answer_contains=["가상자산", "보호", "이용자", "규제"],
        expected_citations_keywords=["가상자산", "이용자보호"],
        ground_truth_summary="가상자산 예치금 분리보관, 이상거래 감시, 불공정거래 규제 등 이용자 보호 강화.",
        tags=["가상자산", "이용자보호"]
    ),
    GoldenQuestion(
        id="GEN-004",
        question="녹색금융 분류체계(택소노미)란?",
        difficulty=QuestionDifficulty.FACTUAL,
        industry=IndustryFocus.GENERAL,
        expected_answer_contains=["녹색", "분류", "택소노미", "환경"],
        expected_citations_keywords=["녹색금융", "택소노미"],
        ground_truth_summary="환경적으로 지속가능한 경제활동을 정의하는 분류체계로, 녹색채권 발행 등에 활용.",
        tags=["녹색금융", "택소노미"]
    ),
    GoldenQuestion(
        id="GEN-005",
        question="금융규제 샌드박스 제도란?",
        difficulty=QuestionDifficulty.FACTUAL,
        industry=IndustryFocus.GENERAL,
        expected_answer_contains=["샌드박스", "규제", "혁신", "특례"],
        expected_citations_keywords=["샌드박스", "금융혁신"],
        ground_truth_summary="혁신적 금융서비스에 대해 일정 기간 규제를 유예하거나 면제하여 시범 운영 허용.",
        tags=["샌드박스", "금융혁신"]
    ),
    GoldenQuestion(
        id="GEN-006",
        question="금융기관 클라우드 이용 규정은?",
        difficulty=QuestionDifficulty.FACTUAL,
        industry=IndustryFocus.GENERAL,
        expected_answer_contains=["클라우드", "규정", "보안", "이용"],
        expected_citations_keywords=["클라우드", "금융권"],
        ground_truth_summary="금융회사의 클라우드 이용 시 보안성 평가, 데이터 국내 보관 등 규정 준수 필요.",
        tags=["클라우드", "IT규제"]
    ),
    GoldenQuestion(
        id="GEN-007",
        question="금융권 AI 활용 가이드라인 내용은?",
        difficulty=QuestionDifficulty.FACTUAL,
        industry=IndustryFocus.GENERAL,
        expected_answer_contains=["AI", "가이드라인", "설명가능", "공정성"],
        expected_citations_keywords=["AI", "인공지능", "가이드라인"],
        ground_truth_summary="AI 모델의 설명가능성, 공정성, 책임성 확보, 소비자 보호 등 원칙 제시.",
        tags=["AI", "가이드라인"]
    ),
    GoldenQuestion(
        id="GEN-008",
        question="금융회사 지배구조법의 주요 내용은?",
        difficulty=QuestionDifficulty.FACTUAL,
        industry=IndustryFocus.GENERAL,
        expected_answer_contains=["지배구조", "이사회", "내부통제", "CEO"],
        expected_citations_keywords=["지배구조법", "금융회사"],
        ground_truth_summary="이사회 구성, CEO 임기, 내부통제, 위험관리 등 금융회사 지배구조 기준 규정.",
        tags=["지배구조", "내부통제"]
    ),
    GoldenQuestion(
        id="GEN-009",
        question="자금세탁방지(AML) 의무사항은?",
        difficulty=QuestionDifficulty.FACTUAL,
        industry=IndustryFocus.GENERAL,
        expected_answer_contains=["자금세탁", "AML", "의무", "고객확인"],
        expected_citations_keywords=["자금세탁방지", "AML"],
        ground_truth_summary="고객확인(CDD), 의심거래보고(STR), 고액현금거래보고(CTR) 등 AML 의무 이행.",
        tags=["AML", "자금세탁방지"]
    ),
    GoldenQuestion(
        id="GEN-010",
        question="금융위원회와 금융감독원의 역할 차이는?",
        difficulty=QuestionDifficulty.FACTUAL,
        industry=IndustryFocus.GENERAL,
        expected_answer_contains=["금융위", "금감원", "역할", "정책", "감독"],
        expected_citations_keywords=["금융위원회", "금융감독원"],
        ground_truth_summary="금융위는 정책 수립 및 제도 설계, 금감원은 실제 검사 및 감독 업무 수행.",
        tags=["금융위", "금감원", "역할"]
    ),
]


def get_golden_dataset() -> List[GoldenQuestion]:
    """Get the full golden dataset."""
    return GOLDEN_DATASET


def get_questions_by_difficulty(difficulty: QuestionDifficulty) -> List[GoldenQuestion]:
    """Get questions filtered by difficulty."""
    return [q for q in GOLDEN_DATASET if q.difficulty == difficulty]


def get_questions_by_industry(industry: IndustryFocus) -> List[GoldenQuestion]:
    """Get questions filtered by industry."""
    return [q for q in GOLDEN_DATASET if q.industry == industry]


def get_dataset_stats() -> Dict[str, Any]:
    """Get statistics about the golden dataset."""
    stats = {
        "total_questions": len(GOLDEN_DATASET),
        "by_difficulty": {},
        "by_industry": {},
        "tags": {}
    }
    
    for q in GOLDEN_DATASET:
        # By difficulty
        d = q.difficulty.value
        stats["by_difficulty"][d] = stats["by_difficulty"].get(d, 0) + 1
        
        # By industry
        i = q.industry.value
        stats["by_industry"][i] = stats["by_industry"].get(i, 0) + 1
        
        # Tags
        for tag in q.tags:
            stats["tags"][tag] = stats["tags"].get(tag, 0) + 1
    
    return stats
