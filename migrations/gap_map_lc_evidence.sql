-- LC 근거(Legal Coverage Evidence): 어떤 법령·조항이 0/0.5/1에 대응하는지 저장
-- RAG 기반 RCC 보강: 근거 보기/내보내기용

ALTER TABLE gap_map_scores
ADD COLUMN IF NOT EXISTS lc_evidence TEXT;

COMMENT ON COLUMN gap_map_scores.lc_evidence IS 'LC 값 근거: 법령명·조항·출처 (예: 전자금융거래법 제xx조, 자본시장법 ...)';
