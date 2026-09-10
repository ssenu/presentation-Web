import json

import pytest

from app.store import Store, slugify


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path)


def test_slugify():
    assert slugify("2026 Q3 리뷰") == "2026-Q3-리뷰"
    assert slugify('a/b\\c:d*e?f"g<h>i|j') == "abcdefghij"
    assert slugify("  ..hidden") == "hidden"
    assert slugify("///") == "item"


def test_empty(store):
    assert store.list() == []


def test_add_and_list(store, tmp_path):
    item = store.add("첫 발표", "회사")
    assert item.slug == "첫-발표"
    assert item.category == "회사"
    assert item.order == 0
    assert [i.slug for i in store.list()] == ["첫-발표"]
    assert (tmp_path / "index.json").exists()
    assert store.item_dir("첫-발표") == tmp_path / "presentations" / "첫-발표"


def test_slug_collision(store):
    store.add("a", "")
    assert store.add("a", "").slug == "a-2"
    assert store.add("a", "").slug == "a-3"


def test_order_increments(store):
    store.add("a", "")
    assert store.add("b", "").order == 1


def test_find_by_title(store):
    store.add("a", "")
    assert store.find_by_title("a").slug == "a"
    assert store.find_by_title("zzz") is None


def test_update(store):
    store.add("a", "")
    item = store.update("a", title="b", category="c")
    assert item.slug == "a" and item.title == "b" and item.category == "c"
    item = store.update("a", category="")
    assert item.title == "b" and item.category == ""


def test_update_missing(store):
    with pytest.raises(KeyError):
        store.update("nope", title="x")


def test_remove(store):
    store.add("a", "")
    store.remove("a")
    assert store.list() == []
    with pytest.raises(KeyError):
        store.remove("a")


def test_reorder(store):
    for t in "abc":
        store.add(t, "")
    store.reorder(["c", "a", "b"])
    assert [(i.slug, i.order) for i in store.list()] == [("c", 0), ("a", 1), ("b", 2)]


def test_reorder_rejects_unknown_or_partial(store):
    store.add("a", "")
    store.add("b", "")
    with pytest.raises(ValueError):
        store.reorder(["a"])
    with pytest.raises(ValueError):
        store.reorder(["a", "x"])


def test_persists_across_instances(tmp_path):
    Store(tmp_path).add("a", "cat")
    again = Store(tmp_path)
    assert again.get("a").category == "cat"
    assert json.loads((tmp_path / "index.json").read_text("utf-8"))["items"][0]["slug"] == "a"
