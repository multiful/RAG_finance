# ======================================================================
# FSC Policy RAG System | 모듈: app.services.policy_simulator
# 최종 수정일: 2026-04-07
# 연관 문서: SYSTEM_ARCHITECTURE.md, RAG_PIPELINE.md, DIRECTORY_SPEC.md
# ======================================================================

"""Policy Simulator Service."""
import json
import logging
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.core.database import get_db
from datetime import datetime, timezone
from app.models.schemas import PolicyDiffResponse, PolicyDiffItem
import openai

logger = logging.getLogger(__name__)

# 업권 키워드 매핑 (industry-impact와 일관성 유지)
INDUSTRY_KEYWORDS: Dict[str, List[str]] = {
    "INSURANCE": ["보험", "손해", "생명", "계약자", "보장", "책임준비금", "K-ICS", "지급여력", "보험료", "상품"],
    "BANKING": ["은행", "예금", "대출", "여신", "수신", "BIS", "LCR", "DSR", "LTV", "가계대출", "금리"],
    "SECURITIES": ["증권", "주식", "채권", "파생", "투자", "공매도", "IPO", "공시", "자본시장", "펀드"],
}


class PolicySimulator:
    """Simulate policy changes between two documents."""
    
    def __init__(self):
        self.db = get_db()
        self.openai_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def simulate(self, old_doc_id: str, new_doc_id: str, theme: Optional[str] = None) -> PolicyDiffResponse:
        """Analyze differences between two policy documents."""
        # 1. Fetch metadata and content
        old_doc = self.db.table("documents").select("title").eq("document_id", old_doc_id).execute()
        new_doc = self.db.table("documents").select("title").eq("document_id", new_doc_id).execute()
        
        old_text = await self._get_doc_text(old_doc_id)
        new_text = await self._get_doc_text(new_doc_id)
        
        old_title = old_doc.data[0]["title"] if old_doc.data else "Old Policy"
        new_title = new_doc.data[0]["title"] if new_doc.data else "New Policy"

        if not old_text or not new_text:
            missing = []
            if not old_text:
                missing.append("문서 A(기준)")
            if not new_text:
                missing.append("문서 B(비교)")
            summary = (
                f"{', '.join(missing)}에 수집·파싱된 본문이 없습니다. "
                "설정에서 수집을 실행한 뒤, 파이프라인에서 파싱·인덱싱이 완료된 문서를 선택해 주세요. "
                "시드 문서를 쓰려면 app/backend에서 python -m scripts.seed_data 를 실행한 뒤, "
                "규제 시뮬레이션에서 '가상자산·토큰증권·스테이블코인 관련만 보기'를 켜고 목록 상단의 문서를 선택해 보세요."
            )
            return PolicyDiffResponse(
                old_doc_title=old_title,
                new_doc_title=new_title,
                changes=[],
                overall_risk="medium",
                summary=summary,
                generated_at=datetime.now(timezone.utc),
            )

        # 2. LLM Analysis — 두 문서의 차이점을 포괄적으로 추출 (규제 변경뿐 아니라 초점·용어·범위 차이 포함)
        theme_instruction = ""
        if theme:
            theme_instruction = f"\n또한 '{theme}' 테마 관점(주요 대상·리스크 축·감독 포인트)에서 특히 중요한 차이점을 강조하세요.\n"

        prompt = f"""두 금융 규제/정책 문서를 비교하여 차이점을 포괄적으로 추출하세요.
조항별 변경(추가/수정/삭제)뿐 아니라, 주제·초점·용어·대상 범위(국내/국제)·강조점 차이도 항목으로 포함하세요.{theme_instruction}
비슷한 내용(유사점)이 있으면 요약에 한 줄로 언급해도 됩니다. 최소 5개 이상의 차이/변경 항목을 나열하세요.

문서 A (기준): {old_title}
본문: {old_text[:6000]}

문서 B (비교): {new_title}
본문: {new_text[:6000]}

반드시 아래 JSON 형식으로만 출력하세요:
{{
  "changes": [
    {{
      "clause": "조항·주제 또는 차이 영역(예: 적용대상, 정의, 의무사항, 시행일 등)",
      "change_type": "added/modified/removed",
      "description": "구체적인 차이점 또는 변경 내용 (한국어, 한 문장 이상)",
      "risk_level": "high/medium/low",
      "impacted_process": "영향을 받는 업무·대상 또는 해당 없으면 '-'"
    }}
  ],
  "overall_risk": "high/medium/low",
  "summary": "두 문서의 차이점 종합 요약 (한국어, 3~5문장). 유사점이 있으면 한 줄 포함."
}}
"""
        try:
            response = await self.openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "당신은 금융 규제·정책 문서 비교 전문가입니다. 두 문서의 차이점을 빠짐없이 추출하고, 조항·주제·용어·범위 차이를 구체적으로 나열하세요."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            if not content or not content.strip():
                raise ValueError("LLM returned empty content")
            data = json.loads(content)
            def _norm_risk(v: str) -> str:
                r = (v or "medium").strip().lower()
                return r if r in ("high", "medium", "low") else "medium"

            raw_changes = data.get("changes") or []
            changes: List[PolicyDiffItem] = []
            for i, item in enumerate(raw_changes):
                if not isinstance(item, dict):
                    continue
                try:
                    changes.append(PolicyDiffItem(
                        clause=str(item.get("clause", "") or ""),
                        change_type=str(item.get("change_type", "modified") or "modified"),
                        description=str(item.get("description", "") or ""),
                        risk_level=_norm_risk(str(item.get("risk_level", "medium") or "medium")),
                        impacted_process=str(item.get("impacted_process", "") or ""),
                    ))
                except Exception as parse_err:
                    logger.debug("PolicyDiffItem skip item %s: %s", i, parse_err)
            risk = (data.get("overall_risk") or "low").strip().lower()
            if risk not in ("high", "medium", "low"):
                risk = "medium"

            industry_impact_delta = self._estimate_industry_impact_delta(changes)
            action_items = self._build_action_items(changes, theme)
            suggested_links = self._build_suggested_checklist_links(changes, theme, industry_impact_delta)

            return PolicyDiffResponse(
                old_doc_title=old_title,
                new_doc_title=new_title,
                changes=changes,
                overall_risk=risk,
                summary=str(data.get("summary") or ""),
                generated_at=datetime.now(timezone.utc),
                action_items=action_items,
                suggested_checklist_links=suggested_links,
                industry_impact_delta=industry_impact_delta,
            )
        except json.JSONDecodeError as e:
            logger.warning("Policy simulate JSON decode error: %s", e)
            return PolicyDiffResponse(
                old_doc_title=old_title,
                new_doc_title=new_title,
                changes=[],
                overall_risk="medium",
                summary=f"분석 결과 파싱 오류: {str(e)}",
                generated_at=datetime.now(timezone.utc),
            )
        except Exception as e:
            logger.exception("Policy Diff Error: %s", e)
            return PolicyDiffResponse(
                old_doc_title=old_title,
                new_doc_title=new_title,
                changes=[],
                overall_risk="medium",
                summary=f"분석 중 오류 발생: {str(e)}",
                generated_at=datetime.now(timezone.utc),
            )

    def _estimate_industry_impact_delta(self, changes: List[PolicyDiffItem]) -> Dict[str, float]:
        """업권별 영향도 추정 (단순 휴리스틱: 키워드 + risk_level 가중치)."""
        weights = {"high": 3.0, "medium": 1.5, "low": 0.5}
        deltas: Dict[str, float] = {k: 0.0 for k in INDUSTRY_KEYWORDS.keys()}

        for c in changes:
            text = " ".join([c.impacted_process or "", c.clause or "", c.description or ""])
            level = (c.risk_level or "medium").strip().lower()
            base = weights.get(level, 0.5)
            for industry, keywords in INDUSTRY_KEYWORDS.items():
                if any(kw in text for kw in keywords):
                    deltas[industry] += base

        # 0인 업권은 제거, 한 자리 소수점으로 제한
        return {k: round(v, 1) for k, v in deltas.items() if v > 0}

    def _build_action_items(self, changes: List[PolicyDiffItem], theme: Optional[str]) -> List[str]:
        """조치안 초안 생성 (high/medium 리스크 중심)."""
        items: List[str] = []
        high_med = [c for c in changes if (c.risk_level or "").lower() in ("high", "medium")]

        for c in high_med[:5]:
            process = (c.impacted_process or "").strip() or "관련 업무 프로세스"
            clause = (c.clause or "").strip() or "해당 조항"
            prefix = f"[테마: {theme}] " if theme else ""
            items.append(
                f"{prefix}{process}에 대한 내부통제·업무 매뉴얼(조항: {clause}) 개정 필요성 검토"
            )

        if not items and changes:
            items.append(
                "변경된 조항 전반에 대해 내부통제 기준·업무 매뉴얼·상품설명서 등을 재점검하세요."
            )
        return items

    def _build_suggested_checklist_links(
        self,
        changes: List[PolicyDiffItem],
        theme: Optional[str],
        industry_impact_delta: Dict[str, float],
    ) -> List[Dict[str, Any]]:
        """샌드박스 체크리스트·Gap Map·Analytics로 이어지는 후속 액션 추천."""
        links: List[Dict[str, Any]] = []

        has_high_med = any((c.risk_level or "").lower() in ("high", "medium") for c in changes)
        if has_high_med:
            links.append(
                {
                    "label": "Sandbox 자가진단 실행",
                    "description": "변경된 규제가 샌드박스 요건·리스크에 미치는 영향을 자가진단합니다.",
                    "type": "sandbox_checklist",
                    "priority": "high",
                }
            )

        # 국제 기준·FSB/BIS 언급 시 Gap Map 추천
        all_text = " ".join((c.description or "") for c in changes)
        if any(kw in all_text for kw in ["FSB", "BIS", "국제", "국외", "글로벌"]):
            links.append(
                {
                    "label": "Gap Map에서 국내·국제 규제 비교",
                    "description": "국내 규제와 국제 기준 간 차이를 Gap Map 대시보드에서 확인합니다.",
                    "type": "gap_map",
                    "priority": "medium",
                }
            )

        if industry_impact_delta:
            links.append(
                {
                    "label": "업권별 영향 대시보드 열기",
                    "description": "Analytics 탭에서 은행·보험·증권별 규제 강도 변화를 확인합니다.",
                    "type": "analytics_industry",
                    "priority": "medium",
                }
            )

        if theme and not any(l.get("label", "").startswith("테마") for l in links):
            links.append(
                {
                    "label": f"테마별 리뷰: {theme}",
                    "description": "선택한 테마 관점에서 추가 검토가 필요한 항목을 정리합니다.",
                    "type": "theme_review",
                    "priority": "low",
                }
            )

        return links

    async def _get_doc_text(self, doc_id: str) -> str:
        """chunks 테이블에서 본문 수집. 없으면 documents.raw_text 폴백 (시드/미파싱 문서 대응)."""
        res = self.db.table("chunks").select("chunk_text").eq("document_id", doc_id).order("chunk_index").limit(30).execute()
        if res.data:
            return "\n\n".join([c["chunk_text"] for c in res.data])
        doc = self.db.table("documents").select("raw_text").eq("document_id", doc_id).execute()
        if doc.data and doc.data[0].get("raw_text"):
            return (doc.data[0]["raw_text"] or "")[:12000]
        return ""

simulator = PolicySimulator()
