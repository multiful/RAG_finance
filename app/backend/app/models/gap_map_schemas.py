"""Gap Map API용 Pydantic 스키마 (KAI Risk–Policy Gap Map)."""
from pydantic import BaseModel, Field
from typing import List, Optional


class RiskAxis(BaseModel):
    """단일 리스크 축 메타정보."""
    axis_id: str = Field(..., description="축 ID (R1~R10)")
    name_ko: str = Field(..., description="한글 축명")


class RiskAxisScore(BaseModel):
    """리스크 축별 GI, LC, Gap 점수."""
    axis_id: str = Field(..., description="축 ID (R1~R10)")
    name_ko: str = Field(..., description="한글 축명")
    gi: float = Field(..., ge=0.0, le=1.0, description="Global Impact (0~1)")
    lc: float = Field(..., ge=0.0, le=1.0, description="Legal Coverage (0=직접규율, 1=미포섭)")
    gap: float = Field(..., ge=0.0, le=1.0, description="Gap = GI × (1 - LC)")


class GapMapResponse(BaseModel):
    """전체 Gap Map 응답."""
    items: List[RiskAxisScore] = Field(default_factory=list, description="축별 점수 목록")
    formula: str = Field(default="Gap = GI × (1 - LC)", description="Gap 산출 공식")


class BlindSpotItem(BaseModel):
    """상위 사각지대 1건."""
    rank: int
    axis_id: str
    name_ko: str
    gap: float
    description: str = ""


class TopBlindSpotsResponse(BaseModel):
    """상위 N대 사각지대 응답."""
    items: List[BlindSpotItem] = Field(default_factory=list)
    formula: str = Field(default="Gap = GI × (1 - LC)", description="Gap 산출 공식")


class GapMapHeatmapRow(BaseModel):
    """Heatmap용 1행: 축 ID + 메트릭 값."""
    axis_id: str
    name_ko: str
    gi: float
    lc: float
    gap: float


class GapMapScoreUpdate(BaseModel):
    """한 축 GI/LC 수정 (관리자 PATCH)."""
    gi: Optional[float] = Field(None, ge=0.0, le=1.0)
    lc: Optional[float] = Field(None, ge=0.0, le=1.0)
    source_or_note: Optional[str] = None
    lc_evidence: Optional[str] = Field(None, description="LC 값 근거: 법령명·조항·출처")


class GapMapScoreItem(BaseModel):
    """축별 점수 1건 (일괄 PUT)."""
    axis_id: str = Field(..., pattern="^R(1|2|3|4|5|6|7|8|9|10)$")
    gi: float = Field(..., ge=0.0, le=1.0)
    lc: float = Field(..., ge=0.0, le=1.0)
    source_or_note: Optional[str] = None
    lc_evidence: Optional[str] = None


class LCEvidenceItem(BaseModel):
    """LC 근거 1축 (보기/내보내기)."""
    axis_id: str
    name_ko: str
    lc: float
    lc_evidence: str = ""
    source_or_note: str = ""


class LCEvidenceResponse(BaseModel):
    """LC 근거 전체 응답."""
    items: List[LCEvidenceItem] = Field(default_factory=list)


class GapMapScoresBulkUpdate(BaseModel):
    """여러 축 일괄 수정 (관리자 PUT)."""
    scores: List[GapMapScoreItem] = Field(..., max_length=10)


class GiComponentItem(BaseModel):
    """GI 국제 데이터 1축: Freq/Rec/Inc/Sys."""
    axis_id: str = Field(..., pattern="^R(1|2|3|4|5|6|7|8|9|10)$")
    freq: float = Field(..., ge=0.0, le=1.0, description="문헌 언급 빈도")
    rec: float = Field(..., ge=0.0, le=1.0, description="권고 강도")
    inc: float = Field(..., ge=0.0, le=1.0, description="사고 연관성")
    sys: float = Field(..., ge=0.0, le=1.0, description="시스템 리스크 기여도")
    source_doc: Optional[str] = Field(None, description="출처 FSB/BIS/IMF/논문 등")


class GiComponentsBulkUpdate(BaseModel):
    """국제 데이터: GI 세부 요소 일괄 입력 (PUT)."""
    components: List[GiComponentItem] = Field(..., max_length=10)
