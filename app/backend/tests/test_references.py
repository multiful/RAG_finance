"""References (KCI) API 단위 테스트."""
import pytest
from fastapi.testclient import TestClient


def test_references_meta(client: TestClient) -> None:
    """GET /api/v1/references -> 200, description·references·kci_style_citations."""
    r = client.get("/api/v1/references")
    assert r.status_code == 200
    data = r.json()
    assert "references" in data or "description" in data
    if "count" in data:
        assert data["count"]["total"] >= 0


def test_references_list(client: TestClient) -> None:
    """GET /api/v1/references?format=list -> 200, items 배열."""
    r = client.get("/api/v1/references?format=list")
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert isinstance(data["items"], list)


def test_references_kci_style(client: TestClient) -> None:
    """GET /api/v1/references/kci-style -> 200, citations 배열."""
    r = client.get("/api/v1/references/kci-style")
    assert r.status_code == 200
    data = r.json()
    assert "citations" in data
    assert isinstance(data["citations"], list)
