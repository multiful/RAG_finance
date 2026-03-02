"""pytest 공통 픽스처: FastAPI TestClient."""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    """FastAPI TestClient. 실제 DB/Redis/OpenAI 연동 시 스킵 가능."""
    return TestClient(app)
