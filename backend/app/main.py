import os
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import auth, items
from .config import Settings, get_settings

app = FastAPI(title="presentation-web")
app.include_router(items.router)


class LoginBody(BaseModel):
    password: str


@app.post("/api/login")
def login(body: LoginBody, response: Response, settings: Settings = Depends(get_settings)):
    if not auth.check_password(settings, body.password):
        raise HTTPException(status_code=401, detail="비밀번호가 틀렸습니다")
    response.set_cookie(
        auth.COOKIE_NAME,
        auth.make_token(settings.secret_key),
        max_age=auth.MAX_AGE,
        httponly=True,
        samesite="lax",
    )
    return {"ok": True}


@app.post("/api/logout")
def logout(response: Response):
    response.delete_cookie(auth.COOKIE_NAME)
    return {"ok": True}


@app.get("/api/me", dependencies=[Depends(auth.require_login)])
def me():
    return {"ok": True}


# 빌드된 Vue 앱 서빙. STATIC_DIR 환경변수 또는 ../../frontend/dist 를 찾는다.
STATIC_DIR = Path(os.environ.get("STATIC_DIR", Path(__file__).resolve().parents[2] / "frontend" / "dist"))

if (STATIC_DIR / "index.html").is_file():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        return FileResponse(STATIC_DIR / "index.html")
