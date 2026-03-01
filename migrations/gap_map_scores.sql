-- Gap Map Scores Table (Phase 1: DB 저장 + 수동 입력)
-- KAI Risk–Policy Gap Map: GI(Global Importance), LC(Local Coverage) 저장
-- Gap = GI × (1 - LC) 는 서비스에서 계산

CREATE TABLE IF NOT EXISTS gap_map_scores (
    axis_id TEXT PRIMARY KEY CHECK (axis_id IN (
        'R1','R2','R3','R4','R5','R6','R7','R8','R9','R10'
    )),
    gi DECIMAL(5,4) NOT NULL CHECK (gi >= 0 AND gi <= 1),
    lc DECIMAL(5,4) NOT NULL CHECK (lc >= 0 AND lc <= 1),
    source_or_note TEXT,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gap_map_scores_updated_at
    ON gap_map_scores(updated_at DESC);

COMMENT ON TABLE gap_map_scores IS 'Risk–Policy Gap Map: 축별 GI/LC (실데이터). 없으면 앱 상수 fallback.';
COMMENT ON COLUMN gap_map_scores.axis_id IS '리스크 축 ID (R1~R10)';
COMMENT ON COLUMN gap_map_scores.gi IS 'Global Importance (0~1)';
COMMENT ON COLUMN gap_map_scores.lc IS 'Local Coverage (0~1)';
COMMENT ON COLUMN gap_map_scores.source_or_note IS '출처 또는 메모 (수동 입력 시)';

-- 시드: 현재 목업 값 (risk_axes.py 기준). 재실행 시 upsert
INSERT INTO gap_map_scores (axis_id, gi, lc, source_or_note) VALUES
    ('R1', 0.50, 0.5, 'KAI 초기값 (목업)'),
    ('R2', 0.56, 0.0, 'KAI 초기값 (목업)'),
    ('R3', 0.64, 0.0, 'KAI 초기값 (목업)'),
    ('R4', 0.50, 0.0, 'KAI 초기값 (목업)'),
    ('R5', 0.54, 0.0, 'KAI 초기값 (목업)'),
    ('R6', 0.45, 0.5, 'KAI 초기값 (목업)'),
    ('R7', 0.40, 0.5, 'KAI 초기값 (목업)'),
    ('R8', 0.55, 0.5, 'KAI 초기값 (목업)'),
    ('R9', 0.48, 0.0, 'KAI 초기값 (목업)'),
    ('R10', 0.42, 0.5, 'KAI 초기값 (목업)')
ON CONFLICT (axis_id) DO UPDATE SET
    gi = EXCLUDED.gi,
    lc = EXCLUDED.lc,
    source_or_note = EXCLUDED.source_or_note,
    updated_at = NOW();
