import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("APP_PASSWORD", "pw")
    monkeypatch.setenv("SECRET_KEY", "s")
    from app.config import get_settings

    get_settings.cache_clear()
    return tmp_path


@pytest.fixture
def client(data_dir):
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth(client):
    r = client.post("/api/login", json={"password": "pw"})
    assert r.status_code == 200
    return client
