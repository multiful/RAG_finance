-- GI 세부 요소 (국제 데이터): Freq, Rec, Inc, Sys
-- GI = 0.3*Freq + 0.3*Rec + 0.2*Inc + 0.2*Sys (0~1)
-- 이 테이블에 행이 있으면 서비스에서 GI를 계산해 사용; 없으면 gap_map_scores.gi 사용

CREATE TABLE IF NOT EXISTS gap_map_gi_components (
    axis_id TEXT PRIMARY KEY CHECK (axis_id IN (
        'R1','R2','R3','R4','R5','R6','R7','R8','R9','R10'
    )),
    freq DECIMAL(5,4) NOT NULL DEFAULT 0 CHECK (freq >= 0 AND freq <= 1),
    rec  DECIMAL(5,4) NOT NULL DEFAULT 0 CHECK (rec  >= 0 AND rec  <= 1),
    inc  DECIMAL(5,4) NOT NULL DEFAULT 0 CHECK (inc  >= 0 AND inc  <= 1),
    sys  DECIMAL(5,4) NOT NULL DEFAULT 0 CHECK (sys  >= 0 AND sys  <= 1),
    source_doc TEXT,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gap_map_gi_components_updated_at
    ON gap_map_gi_components(updated_at DESC);

COMMENT ON TABLE gap_map_gi_components IS 'GI 국제 데이터: Freq/Rec/Inc/Sys. 있으면 GI 자동 계산, 없으면 gap_map_scores.gi 사용';
COMMENT ON COLUMN gap_map_gi_components.freq IS '문헌 언급 빈도 (0~1)';
COMMENT ON COLUMN gap_map_gi_components.rec IS '권고 강도 (0~1)';
COMMENT ON COLUMN gap_map_gi_components.inc IS '사고 연관성 (0~1)';
COMMENT ON COLUMN gap_map_gi_components.sys IS '시스템 리스크 기여도 (0~1)';
COMMENT ON COLUMN gap_map_gi_components.source_doc IS '출처 (FSB, BIS, IMF, 논문 등)';

-- 시드: 예시 2축만. 나머지는 API로 추가
INSERT INTO gap_map_gi_components (axis_id, freq, rec, inc, sys, source_doc) VALUES
    ('R3', 0.70, 0.65, 0.60, 0.62, 'FSB 2024 High-level recommendations; BIS stablecoin report'),
    ('R5', 0.68, 0.55, 0.50, 0.52, 'FSB 2024; IMF policy note')
ON CONFLICT (axis_id) DO UPDATE SET
    freq = EXCLUDED.freq,
    rec  = EXCLUDED.rec,
    inc  = EXCLUDED.inc,
    sys  = EXCLUDED.sys,
    source_doc = EXCLUDED.source_doc,
    updated_at = NOW();
