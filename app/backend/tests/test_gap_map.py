"""Gap Map API 단위 테스트."""
import pytest
from fastapi.testclient import TestClient


def test_gap_map(client: TestClient) -> None:
    """GET /api/v1/gap-map -> 200. items 또는 fallback 구조."""
    r = client.get("/api/v1/gap-map")
    assert r.status_code == 200
    data = r.json()
    assert "items" in data or "formula" in data or (isinstance(data, list) and len(data) >= 0)


def test_gap_map_top_blind_spots(client: TestClient) -> None:
    """GET /api/v1/gap-map/top-blind-spots -> 200."""
    r = client.get("/api/v1/gap-map/top-blind-spots?limit=3")
    assert r.status_code == 200
    data = r.json()
    assert "items" in data or isinstance(data, list)


def test_gap_map_heatmap(client: TestClient) -> None:
    """GET /api/v1/gap-map/heatmap -> 200."""
    r = client.get("/api/v1/gap-map/heatmap")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
