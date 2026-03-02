-- RAGAS Evaluation History Table
-- 평가 결과를 저장하여 성능 추이를 추적합니다

CREATE TABLE IF NOT EXISTS evaluation_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    faithfulness DECIMAL(5,4) NOT NULL,
    answer_relevancy DECIMAL(5,4) NOT NULL,
    context_precision DECIMAL(5,4) NOT NULL,
    context_recall DECIMAL(5,4) NOT NULL,
    overall_score DECIMAL(5,4) NOT NULL,
    sample_size INTEGER NOT NULL DEFAULT 8,
    details JSONB,
    evaluated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_evaluation_history_evaluated_at 
    ON evaluation_history(evaluated_at DESC);

COMMENT ON TABLE evaluation_history IS 'RAGAS 자동 평가 결과 기록';
COMMENT ON COLUMN evaluation_history.faithfulness IS '답변의 문서 충실도 (0-1)';
COMMENT ON COLUMN evaluation_history.answer_relevancy IS '답변과 질문의 관련성 (0-1)';
COMMENT ON COLUMN evaluation_history.context_precision IS '검색 컨텍스트의 정밀도 (0-1)';
COMMENT ON COLUMN evaluation_history.context_recall IS '검색 컨텍스트의 재현율 (0-1)';
COMMENT ON COLUMN evaluation_history.overall_score IS '종합 점수 (0-1)';
COMMENT ON COLUMN evaluation_history.sample_size IS '평가에 사용된 테스트 케이스 수';
COMMENT ON COLUMN evaluation_history.details IS '개별 테스트 케이스 결과 (JSON)';
