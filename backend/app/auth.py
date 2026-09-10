import secrets

from fastapi import Cookie, Depends, HTTPException
from itsdangerous import BadSignature, TimestampSigner

from .config import Settings, get_settings

COOKIE_NAME = "session"
# 세션 쿠키(브라우저를 닫으면 삭제)이지만, 토큰 자체도 이 시간이 지나면 무효가 된다.
MAX_AGE = 12 * 60 * 60


def make_token(secret: str) -> str:
    return TimestampSigner(secret).sign("ok").decode()


def verify_token(secret: str, token: str) -> bool:
    try:
        TimestampSigner(secret).unsign(token, max_age=MAX_AGE)
        return True
    except BadSignature:
        return False


def check_password(settings: Settings, password: str) -> bool:
    return secrets.compare_digest(settings.app_password, password)


def require_login(
    session: str | None = Cookie(default=None, alias=COOKIE_NAME),
    settings: Settings = Depends(get_settings),
) -> None:
    if not session or not verify_token(settings.secret_key, session):
        raise HTTPException(status_code=401, detail="로그인이 필요합니다")
