def test_login_sets_cookie_and_me_ok(client):
    r = client.post("/api/login", json={"password": "pw"})
    assert r.status_code == 200
    assert "session" in r.cookies
    assert client.get("/api/me").status_code == 200


def test_wrong_password(client):
    r = client.post("/api/login", json={"password": "nope"})
    assert r.status_code == 401
    assert client.get("/api/me").status_code == 401


def test_me_without_cookie(client):
    assert client.get("/api/me").status_code == 401


def test_logout(auth):
    assert auth.post("/api/logout").status_code == 200
    assert auth.get("/api/me").status_code == 401


def test_tampered_cookie(client):
    client.cookies.set("session", "garbage")
    assert client.get("/api/me").status_code == 401


def test_defaults_when_env_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.delenv("APP_PASSWORD", raising=False)
    monkeypatch.delenv("SECRET_KEY", raising=False)
    from app.config import get_settings

    get_settings.cache_clear()
    s = get_settings()
    assert s.app_password == "password"
    assert len(s.secret_key) >= 32
    assert (tmp_path / "secret_key").read_text().strip() == s.secret_key
    # 다시 읽어도 같은 키를 쓴다 (세션이 재시작 후에도 유지됨)
    get_settings.cache_clear()
    assert get_settings().secret_key == s.secret_key


def test_head_root_is_allowed(client):
    assert client.head("/").status_code in (200, 404)
    assert client.head("/api/health").status_code == 200
    assert client.get("/api/health").json() == {"ok": True}


def test_login_cookie_is_session_only(client):
    r = client.post("/api/login", json={"password": "pw"})
    set_cookie = r.headers["set-cookie"].lower()
    assert "max-age" not in set_cookie
    assert "expires" not in set_cookie
    assert "httponly" in set_cookie
