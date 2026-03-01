"""QA API 단위 테스트."""
import pytest
from fastapi.testclient import TestClient


def test_qa_missing_body(client: TestClient) -> None:
    """POST /api/v1/qa body 없음 -> 422."""
    r = client.post("/api/v1/qa", json={})
    assert r.status_code == 422


def test_qa_invalid_body(client: TestClient) -> None:
    """POST /api/v1/qa question 필드 없음 -> 422."""
    r = client.post("/api/v1/qa", json={"compliance_mode": True})
    assert r.status_code == 422


def test_qa_valid_body(client: TestClient) -> None:
    """POST /api/v1/qa 정상 body -> 200(정상) 또는 500(키/DB 미설정)."""
    r = client.post("/api/v1/qa", json={"question": "스테이블코인 규제 현황은?"})
    assert r.status_code in (200, 500)
    if r.status_code == 200:
        data = r.json()
        assert "answer" in data
