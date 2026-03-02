"""Health·Root API 단위 테스트."""
import pytest
from fastapi.testclient import TestClient


def test_root(client: TestClient) -> None:
    """GET / -> 200, name·version·docs 포함."""
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert "name" in data
    assert "version" in data
    assert "docs" in data
    assert "services" in data or "endpoints" in data


def test_health(client: TestClient) -> None:
    """GET /health -> 200, status·services·metrics 구조."""
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert "status" in data
    assert data["status"] in ("healthy", "degraded", "warning")
    assert "services" in data
    assert "api" in data["services"]
    assert "metrics" in data
    assert "documents_count" in data["metrics"] or "timestamp" in data
