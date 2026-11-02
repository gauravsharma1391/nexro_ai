import pytest
from fastapi.testclient import TestClient

from app.core import db
from app.main import app


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXORA_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "100000")
    for k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "LLM_PROVIDER"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    db.init()


@pytest.fixture()
def client():
    return TestClient(app)
