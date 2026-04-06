# ======================================================================
# FSC Policy RAG System | 모듈: app.api.policy_route
# 최종 수정일: 2026-04-07
# 연관 문서: SYSTEM_ARCHITECTURE.md, RAG_PIPELINE.md, DIRECTORY_SPEC.md
# ======================================================================

@router.post("/policy/simulate")
async def simulate_policy_change(body: dict):
    """Simulate impact of policy changes."""
    from app.services.policy_simulator import simulator
    try:
        return await simulator.simulate_change(body.get("old_document_id"), body.get("new_document_id"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
