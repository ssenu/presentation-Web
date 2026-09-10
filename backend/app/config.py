import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel


class Settings(BaseModel):
    data_dir: Path
    app_password: str
    secret_key: str


@lru_cache
def get_settings() -> Settings:
    password = os.environ.get("APP_PASSWORD")
    secret = os.environ.get("SECRET_KEY")
    if not password or not secret:
        raise RuntimeError("APP_PASSWORD and SECRET_KEY must be set")
    return Settings(
        data_dir=Path(os.environ.get("DATA_DIR", "/data")),
        app_password=password,
        secret_key=secret,
    )
