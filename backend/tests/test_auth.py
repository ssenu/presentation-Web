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
