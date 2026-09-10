from fastapi import Depends, FastAPI, HTTPException, Response
from pydantic import BaseModel

from . import auth
from .config import Settings, get_settings

app = FastAPI(title="presentation-web")


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
