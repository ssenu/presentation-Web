import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .auth import require_login
from .config import Settings, get_settings
from .store import Item, Store
from .uploads import UploadError, store_upload

router = APIRouter(dependencies=[Depends(require_login)])


def get_store(settings: Settings = Depends(get_settings)) -> Store:
    return Store(settings.data_dir)


class PatchBody(BaseModel):
    title: str | None = None
    category: str | None = None


class OrderBody(BaseModel):
    slugs: list[str]


@router.get("/api/items", response_model=list[Item])
def list_items(store: Store = Depends(get_store)):
    return store.list()


@router.post("/api/items", response_model=Item)
async def upload_item(
    response: Response,
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    category: str | None = Form(default=None),
    store: Store = Depends(get_store),
):
    title = (title or "").strip() or Path(file.filename or "presentation").stem
    data = await file.read()

    existing = store.find_by_title(title)
    if existing is not None:
        target = existing
        status = 200
    else:
        target = store.add(title, (category or "").strip())
        status = 201

    try:
        store_upload(file.filename or "", data, store.item_dir(target.slug))
    except UploadError as e:
        if existing is None:
            store.remove(target.slug)
        raise HTTPException(status_code=e.status_code, detail=e.detail)

    response.status_code = status
    return target


@router.patch("/api/items/{slug}", response_model=Item)
def patch_item(slug: str, body: PatchBody, store: Store = Depends(get_store)):
    if body.title is not None and not body.title.strip():
        raise HTTPException(status_code=400, detail="제목은 비울 수 없습니다")
    try:
        return store.update(
            slug,
            title=body.title.strip() if body.title is not None else None,
            category=body.category.strip() if body.category is not None else None,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="항목이 없습니다")


@router.delete("/api/items/{slug}", status_code=204)
def delete_item(slug: str, store: Store = Depends(get_store)):
    try:
        store.remove(slug)
    except KeyError:
        raise HTTPException(status_code=404, detail="항목이 없습니다")
    folder = store.item_dir(slug)
    if folder.exists():
        shutil.rmtree(folder)
    return Response(status_code=204)


@router.put("/api/items/order")
def reorder_items(body: OrderBody, store: Store = Depends(get_store)):
    try:
        store.reorder(body.slugs)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}


@router.get("/p/{slug}/{path:path}")
def serve_presentation(slug: str, path: str, store: Store = Depends(get_store)):
    if store.get(slug) is None:
        raise HTTPException(status_code=404, detail="항목이 없습니다")
    base = store.item_dir(slug).resolve()
    target = (base / (path or "index.html")).resolve()
    if base != target and base not in target.parents:
        raise HTTPException(status_code=404, detail="파일이 없습니다")
    if target.is_dir():
        target = target / "index.html"
    if not target.is_file():
        raise HTTPException(status_code=404, detail="파일이 없습니다")
    return FileResponse(target)
