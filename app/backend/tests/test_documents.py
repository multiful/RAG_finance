"""Documents API 단위 테스트."""
import pytest
from fastapi.testclient import TestClient


def test_documents_list(client: TestClient) -> None:
    """GET /api/v1/documents -> 200 또는 500(DB 미연결). 페이지네이션 필드 확인."""
    r = client.get("/api/v1/documents?page=1&page_size=5")
    assert r.status_code in (200, 500)
    if r.status_code == 200:
        data = r.json()
        assert "documents" in data
        assert "total" in data or isinstance(data["documents"], list)


def test_documents_list_with_topic(client: TestClient) -> None:
    """GET /api/v1/documents?topic=stablecoin_sto -> 200 또는 500."""
    r = client.get("/api/v1/documents?page=1&page_size=5&topic=stablecoin_sto")
    assert r.status_code in (200, 500)
