from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path

from pydantic import BaseModel

_FORBIDDEN = re.compile(r'[/\\:*?"<>|]')


def slugify(title: str) -> str:
    s = _FORBIDDEN.sub("", title.strip())
    s = re.sub(r"\s+", "-", s)
    s = s.lstrip(".")
    return s or "item"


class Item(BaseModel):
    slug: str
    title: str
    category: str = ""
    order: int


class Store:
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.index_path = self.data_dir / "index.json"
        self.presentations_dir = self.data_dir / "presentations"
        self.presentations_dir.mkdir(parents=True, exist_ok=True)
        self._items, self._categories = self._load()

    def _load(self) -> tuple[list[Item], list[str]]:
        if not self.index_path.exists():
            return [], []
        raw = json.loads(self.index_path.read_text("utf-8"))
        items = [Item(**i) for i in raw.get("items", [])]
        categories = [str(c) for c in raw.get("categories", [])]
        # 예전 데이터에는 카테고리 목록이 없으므로 항목에서 보충한다.
        for it in items:
            if it.category and it.category not in categories:
                categories.append(it.category)
        return items, categories

    def _save(self) -> None:
        payload = {"categories": self._categories, "items": [i.model_dump() for i in self._items]}
        fd, tmp = tempfile.mkstemp(dir=self.data_dir, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.index_path)

    def item_dir(self, slug: str) -> Path:
        return self.presentations_dir / slug

    def list(self) -> list[Item]:
        return sorted(self._items, key=lambda i: i.order)

    def get(self, slug: str) -> Item | None:
        return next((i for i in self._items if i.slug == slug), None)

    def find_by_title(self, title: str) -> Item | None:
        return next((i for i in self._items if i.title == title), None)

    def _unique_slug(self, base: str) -> str:
        slug, n = base, 1
        while self.get(slug) is not None or self.item_dir(slug).exists():
            n += 1
            slug = f"{base}-{n}"
        return slug

    def add(self, title: str, category: str = "") -> Item:
        order = max((i.order for i in self._items), default=-1) + 1
        item = Item(slug=self._unique_slug(slugify(title)), title=title, category=category, order=order)
        self._items.append(item)
        self._register_category(category)
        self._save()
        return item

    def update(self, slug: str, title: str | None = None, category: str | None = None) -> Item:
        item = self.get(slug)
        if item is None:
            raise KeyError(slug)
        if title is not None:
            item.title = title
        if category is not None:
            item.category = category
            self._register_category(category)
        self._save()
        return item

    # ---- 카테고리 ----
    def categories(self) -> list[str]:
        return list(self._categories)

    def _register_category(self, name: str) -> None:
        if name and name not in self._categories:
            self._categories.append(name)

    def add_category(self, name: str) -> str:
        name = name.strip()
        if not name:
            raise ValueError("카테고리 이름을 입력하세요")
        if name in self._categories:
            raise ValueError("이미 있는 카테고리입니다")
        self._categories.append(name)
        self._save()
        return name

    def remove_category(self, name: str) -> None:
        if name not in self._categories:
            raise KeyError(name)
        if any(i.category == name for i in self._items):
            raise ValueError("파일이 들어 있는 카테고리는 지울 수 없습니다")
        self._categories.remove(name)
        self._save()

    def remove(self, slug: str) -> None:
        item = self.get(slug)
        if item is None:
            raise KeyError(slug)
        self._items.remove(item)
        self._save()

    def reorder(self, slugs: list[str]) -> None:
        if sorted(slugs) != sorted(i.slug for i in self._items):
            raise ValueError("slug 목록이 저장된 항목과 일치하지 않습니다")
        for n, slug in enumerate(slugs):
            self.get(slug).order = n
        self._save()
