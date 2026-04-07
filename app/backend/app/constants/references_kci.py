# ======================================================================
# FSC Policy RAG System | 모듈: app.constants.references_kci
# 최종 수정일: 2026-04-07
# 연관 문서: CHANGE_CONTROL.md, ROOT_DOC_GUIDE.md, SYSTEM_ARCHITECTURE.md, RAG_PIPELINE.md, DIRECTORY_SPEC.md
# 참조 규칙: 루트 MD 계약과 충돌 시 CHANGE_CONTROL.md §5 우선.
# ======================================================================

"""
연구 참고문헌 (KCI·학술 인용용).

competition 문서(스테이블코인–STO 결합 Risk–Policy Gap Map 및 Sandbox Framework) 전반에서
인용된 참고문헌을 정리. KCI(한국학술지인용색인) 및 논문/보고서 작성 시 인용 목록으로 활용.
- type: international_org | domestic_law | domestic_guideline | domestic_org | paper
"""
from typing import List, Dict, Any

# 국제기구·권고안 (FSB, BIS, IMF 등)
REFERENCES_INTERNATIONAL: List[Dict[str, Any]] = [
    {"author": "FSB", "year": 2023, "title_en": "High-level Recommendations for Global Stablecoin Arrangements", "title_ko": "글로벌 스테이블코인 준비에 대한 고위급 권고", "type": "international_org", "note": "GSC 10대 권고"},
    {"author": "FSB", "year": 2023, "title_en": "High-level Recommendations for the Regulation, Supervision and Oversight of Global Stablecoin Arrangements", "title_ko": None, "type": "international_org", "note": "규제·감독 권고"},
    {"author": "FSB", "year": 2023, "title_en": "Global Importance Scoring Methodology", "title_ko": None, "type": "international_org", "note": "GI 산출 방법론"},
    {"author": "FSB", "year": 2023, "title_en": "SupTech Applications in Financial Supervision", "title_ko": None, "type": "international_org", "note": None},
    {"author": "FSB", "year": 2023, "title_en": "Artificial Intelligence and Machine Learning in Financial Services", "title_ko": None, "type": "international_org", "note": None},
    {"author": "FSB", "year": 2024, "title_en": "SupTech Implementation Roadmap", "title_ko": None, "type": "international_org", "note": None},
    {"author": "BIS", "year": 2024, "title_en": "Stablecoin Regulation Framework", "title_ko": None, "type": "international_org", "note": None},
    {"author": "BIS", "year": 2024, "title_en": "Risk Assessment Framework for Digital Assets", "title_ko": None, "type": "international_org", "note": None},
    {"author": "BIS", "year": 2024, "title_en": "Stablecoin-related yields: regulatory approaches", "title_ko": None, "type": "international_org", "note": None},
    {"author": "BIS Innovation Hub", "year": 2023, "title_en": "RegTech Solutions for Regulatory Compliance", "title_ko": None, "type": "international_org", "note": None},
    {"author": "BIS Innovation Hub", "year": 2023, "title_en": "Central bank digital currencies and stablecoins", "title_ko": None, "type": "international_org", "note": None},
    {"author": "IMF-FSB", "year": 2023, "title_en": "Synthesis Paper: Policies for Crypto-assets", "title_ko": "암호자산 정책 통합 보고서", "type": "international_org", "note": "Same Activity, Same Risk, Same Regulation"},
    {"author": "IMF", "year": 2024, "title_en": "Artificial Intelligence in Financial Regulation", "title_ko": None, "type": "international_org", "note": None},
    {"author": "IMF", "year": 2025, "title_en": "How Stablecoins Can Improve Payments and Global Finance", "title_ko": None, "type": "international_org", "note": None},
]

# 국내 법령·가이드라인·당국
REFERENCES_DOMESTIC: List[Dict[str, Any]] = [
    {"author": "금융위원회", "year": 2023, "title_ko": "토큰증권 발행·유통 규율체계 정비방안", "title_en": None, "type": "domestic_guideline", "note": None},
    {"author": "금융위원회", "year": 2025, "title_ko": "디지털 금융 혁신 로드맵", "title_en": None, "type": "domestic_guideline", "note": None},
    {"author": "금융감독원", "year": 2024, "title_ko": "가상자산 감독 가이드라인", "title_en": None, "type": "domestic_guideline", "note": None},
    {"author": "금융감독원", "year": 2024, "title_ko": "SupTech 도입 가이드라인", "title_en": None, "type": "domestic_guideline", "note": None},
    {"author": None, "year": 2024, "title_ko": "가상자산이용자보호법", "title_en": None, "type": "domestic_law", "note": None},
    {"author": None, "year": 2024, "title_ko": "가상자산이용자보호법 시행령", "title_en": None, "type": "domestic_law", "note": None},
]

# 학술 논문·연구 (competition 문서 인용)
REFERENCES_PAPERS: List[Dict[str, Any]] = [
    {"author": "Lambert et al.", "year": 2022, "title_en": "Security Token Offerings", "title_ko": "유럽 STO 전수 데이터 분석", "type": "paper", "note": None},
    {"author": "Bongini et al.", "year": 2022, "title_en": "STO Success Factors", "title_ko": "유럽 11개국 규제 프레임워크 비교", "type": "paper", "note": None},
    {"author": "Ling", "year": 2025, "title_en": "Stablecoin Run Risk", "title_ko": None, "type": "paper", "note": None},
    {"author": "Jacewitz", "year": 2025, "title_en": "Stablecoin Reserve Assets", "title_ko": None, "type": "paper", "note": "예금보험 비용 220배 등"},
    {"author": "Ling et al.", "year": 2025, "title_en": "Stablecoin Run Risk Analysis", "title_ko": None, "type": "paper", "note": "FSB GSC 권고 기반 런 리스크 모델"},
    {"author": "Zhang et al.", "year": 2024, "title_en": "Regulatory Compliance Checking Framework", "title_ko": None, "type": "paper", "note": "RCC"},
    {"author": "Rajpurkar et al.", "year": 2016, "title_en": "SQuAD: 100,000+ Questions for Machine Reading Comprehension", "title_ko": None, "type": "paper", "note": None},
    {"author": "Lin et al.", "year": 2022, "title_en": "TruthfulQA: Measuring How Models Mimic Human Falsehoods", "title_ko": None, "type": "paper", "note": None},
]


def get_all_references() -> List[Dict[str, Any]]:
    """전체 참고문헌 (국제 → 국내 → 논문 순)."""
    items = []
    for r in REFERENCES_INTERNATIONAL:
        items.append({**r, "category": "international"})
    for r in REFERENCES_DOMESTIC:
        items.append({**r, "category": "domestic"})
    for r in REFERENCES_PAPERS:
        items.append({**r, "category": "paper"})
    return items


def get_references_for_kci_style() -> List[Dict[str, Any]]:
    """KCI 인용용: 저자(연도). 제목. 형식으로 정리된 문자열 포함."""
    out = []
    for i, r in enumerate(get_all_references(), 1):
        author = r.get("author") or ""
        year = r.get("year", "")
        title = r.get("title_ko") or r.get("title_en") or ""
        # KCI 스타일 유사: 저자(연도). 제목. [유형]
        entry = f"{author}({year}). {title}"
        if r.get("note"):
            entry += f". [{r['note']}]"
        out.append({
            "index": i,
            "citation_text": entry,
            "author": author,
            "year": year,
            "title_ko": r.get("title_ko"),
            "title_en": r.get("title_en"),
            "type": r.get("type"),
            "category": r.get("category"),
        })
    return out


def get_references_meta() -> Dict[str, Any]:
    """API용: 참고문헌 메타 및 전체 목록."""
    return {
        "description": "스테이블코인–STO 결합 Risk–Policy Gap Map 및 Sandbox Framework 연구 참고문헌 (KCI·인용용)",
        "source": "competition 문서 전반 (page_1, 6, 18, 24, 25, 26, 27, 28, 29 등)",
        "categories": {
            "international": "국제기구(FSB, BIS, IMF 등) 권고안·보고서",
            "domestic": "국내 법령·금융위원회·금융감독원 가이드라인",
            "paper": "학술 논문·선행연구",
        },
        "count": {
            "international": len(REFERENCES_INTERNATIONAL),
            "domestic": len(REFERENCES_DOMESTIC),
            "paper": len(REFERENCES_PAPERS),
            "total": len(REFERENCES_INTERNATIONAL) + len(REFERENCES_DOMESTIC) + len(REFERENCES_PAPERS),
        },
        "references": get_all_references(),
        "kci_style_citations": get_references_for_kci_style(),
    }
