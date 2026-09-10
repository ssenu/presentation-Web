import io
import zipfile


def make_zip(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in files.items():
            z.writestr(name, data)
    return buf.getvalue()


def upload(client, title=None, category=None, files=None, filename="deck.zip"):
    data = {}
    if title is not None:
        data["title"] = title
    if category is not None:
        data["category"] = category
    body = make_zip(files or {"index.html": b"<h1>deck</h1>", "a.css": b"c"})
    return client.post("/api/items", data=data, files={"file": (filename, body, "application/zip")})


def test_requires_login(client):
    assert client.get("/api/items").status_code == 401
    assert client.post("/api/items").status_code == 401
    assert client.get("/p/x/").status_code == 401


def test_upload_and_list_and_serve(auth):
    r = upload(auth, title="첫 발표", category="회사")
    assert r.status_code == 201, r.text
    item = r.json()
    assert item["slug"] == "첫-발표" and item["category"] == "회사"
    items = auth.get("/api/items").json()
    assert [i["slug"] for i in items] == ["첫-발표"]
    r = auth.get("/p/첫-발표/")
    assert r.status_code == 200 and b"<h1>deck</h1>" in r.content
    assert "text/html" in r.headers["content-type"]
    assert auth.get("/p/첫-발표/a.css").content == b"c"
    assert auth.get("/p/첫-발표/missing.png").status_code == 404
    assert auth.get("/p/nope/").status_code == 404


def test_title_defaults_to_filename(auth):
    r = upload(auth, filename="My Deck.zip")
    assert r.status_code == 201
    assert r.json()["title"] == "My Deck"


def test_bad_zip_returns_400(auth):
    r = auth.post("/api/items", files={"file": ("x.zip", b"junk", "application/zip")})
    assert r.status_code == 400


def test_missing_index_returns_400_and_no_item(auth):
    r = upload(auth, title="x", files={"readme.txt": b"r"})
    assert r.status_code == 400
    assert auth.get("/api/items").json() == []


def test_overwrite_keeps_slug_and_meta(auth, data_dir):
    upload(auth, title="a", category="c1")
    auth.put("/api/items/order", json={"slugs": ["a"]})
    r = upload(auth, title="a", files={"index.html": b"v2"})
    assert r.status_code == 200
    assert r.json()["slug"] == "a" and r.json()["category"] == "c1"
    assert len(auth.get("/api/items").json()) == 1
    assert auth.get("/p/a/").content == b"v2"


def test_patch(auth):
    upload(auth, title="a")
    r = auth.patch("/api/items/a", json={"title": "b", "category": "cat"})
    assert r.status_code == 200
    assert r.json() == {"slug": "a", "title": "b", "category": "cat", "order": 0}
    assert auth.patch("/api/items/zzz", json={"title": "b"}).status_code == 404


def test_delete_removes_folder(auth, data_dir):
    upload(auth, title="a")
    assert (data_dir / "presentations" / "a" / "index.html").exists()
    assert auth.delete("/api/items/a").status_code == 204
    assert not (data_dir / "presentations" / "a").exists()
    assert auth.get("/api/items").json() == []
    assert auth.delete("/api/items/a").status_code == 404


def test_reorder(auth):
    for t in "abc":
        upload(auth, title=t)
    r = auth.put("/api/items/order", json={"slugs": ["c", "a", "b"]})
    assert r.status_code == 200
    assert [i["slug"] for i in auth.get("/api/items").json()] == ["c", "a", "b"]
    assert auth.put("/api/items/order", json={"slugs": ["a"]}).status_code == 400


def test_serve_blocks_traversal(auth, data_dir):
    upload(auth, title="a")
    (data_dir / "secret.txt").write_text("s")
    r = auth.get("/p/a/%2e%2e/%2e%2e/secret.txt")
    assert r.status_code in (400, 404)
    # httpx가 경로를 정규화해 /secret.txt 로 보내므로 SPA 셸이 응답할 수 있다. 비밀 내용만 아니면 된다.
    r = auth.get("/p/a/../../secret.txt")
    assert r.content != b"s"
