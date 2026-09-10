import io
import zipfile

import pytest

from app import uploads
from app.uploads import UploadError, extract_presentation


def make_zip(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in files.items():
            z.writestr(name, data)
    return buf.getvalue()


def test_top_level_index(tmp_path):
    dest = tmp_path / "p"
    extract_presentation(make_zip({"index.html": b"<h1>hi</h1>", "img/a.png": b"x"}), dest)
    assert (dest / "index.html").read_bytes() == b"<h1>hi</h1>"
    assert (dest / "img" / "a.png").read_bytes() == b"x"


def test_wrapped_in_single_folder(tmp_path):
    dest = tmp_path / "p"
    extract_presentation(make_zip({"deck/index.html": b"<p>a</p>", "deck/css/s.css": b"c"}), dest)
    assert (dest / "index.html").read_bytes() == b"<p>a</p>"
    assert (dest / "css" / "s.css").read_bytes() == b"c"


def test_missing_index(tmp_path):
    with pytest.raises(UploadError) as e:
        extract_presentation(make_zip({"readme.txt": b"x"}), tmp_path / "p")
    assert e.value.status_code == 400
    assert not (tmp_path / "p").exists()


def test_nested_too_deep_is_rejected(tmp_path):
    with pytest.raises(UploadError) as e:
        extract_presentation(make_zip({"a/b/index.html": b"x"}), tmp_path / "p")
    assert e.value.status_code == 400


def test_path_traversal(tmp_path):
    with pytest.raises(UploadError) as e:
        extract_presentation(make_zip({"index.html": b"x", "../evil.txt": b"e"}), tmp_path / "p")
    assert e.value.status_code == 400
    assert not (tmp_path / "evil.txt").exists()


def test_absolute_path(tmp_path):
    with pytest.raises(UploadError) as e:
        extract_presentation(make_zip({"index.html": b"x", "/etc/passwd": b"e"}), tmp_path / "p")
    assert e.value.status_code == 400


def test_invalid_zip(tmp_path):
    with pytest.raises(UploadError) as e:
        extract_presentation(b"not a zip", tmp_path / "p")
    assert e.value.status_code == 400


def test_replaces_existing_dest(tmp_path):
    dest = tmp_path / "p"
    dest.mkdir()
    (dest / "old.txt").write_text("old")
    extract_presentation(make_zip({"index.html": b"new"}), dest)
    assert not (dest / "old.txt").exists()
    assert (dest / "index.html").read_bytes() == b"new"


def test_size_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(uploads, "MAX_TOTAL_BYTES", 10)
    with pytest.raises(UploadError) as e:
        extract_presentation(make_zip({"index.html": b"x" * 11}), tmp_path / "p")
    assert e.value.status_code == 413
