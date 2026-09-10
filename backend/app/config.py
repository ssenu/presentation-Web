import logging
import os
import secrets
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

log = logging.getLogger("uvicorn.error")

DEFAULT_PASSWORD = "password"


class Settings(BaseModel):
    data_dir: Path
    app_password: str
    secret_key: str


def _load_or_create_secret(data_dir: Path) -> str:
    """SECRET_KEY 환경변수가 없으면 data 폴더에 키를 만들어 두고 재사용한다."""
    path = data_dir / "secret_key"
    if path.exists():
        key = path.read_text("utf-8").strip()
        if key:
            return key
    data_dir.mkdir(parents=True, exist_ok=True)
    key = secrets.token_hex(32)
    path.write_text(key, "utf-8")
    log.warning("SECRET_KEY가 없어 %s 에 새 키를 만들었습니다", path)
    return key


@lru_cache
def get_settings() -> Settings:
    data_dir = Path(os.environ.get("DATA_DIR", "/data"))
    password = os.environ.get("APP_PASSWORD") or DEFAULT_PASSWORD
    if password == DEFAULT_PASSWORD:
        log.warning("APP_PASSWORD가 설정되지 않아 기본값 '%s' 을 사용합니다", DEFAULT_PASSWORD)
    secret = os.environ.get("SECRET_KEY") or _load_or_create_secret(data_dir)
    return Settings(data_dir=data_dir, app_password=password, secret_key=secret)
