@router.post("/policy/simulate")
async def simulate_policy_change(body: dict):
    """Simulate impact of policy changes."""
    from app.services.policy_simulator import simulator
    try:
        return await simulator.simulate_change(body.get("old_document_id"), body.get("new_document_id"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
