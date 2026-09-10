import io
import shutil
import zipfile
from pathlib import Path, PurePosixPath

MAX_TOTAL_BYTES = 200 * 1024 * 1024


class UploadError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _safe_parts(name: str) -> tuple[str, ...]:
    p = PurePosixPath(name.replace(chr(92), "/"))
    if p.is_absolute() or any(part in ("..", "") for part in p.parts):
        raise UploadError(400, f"zip 안에 허용되지 않는 경로가 있습니다: {name}")
    return p.parts


def _find_root(entries: list[tuple[zipfile.ZipInfo, tuple[str, ...]]]) -> tuple[str, ...]:
    files = [parts for info, parts in entries if not info.is_dir()]
    if ("index.html",) in files:
        return ()
    top = {parts[0] for parts in files}
    if len(top) == 1:
        root = next(iter(top))
        if (root, "index.html") in files:
            return (root,)
    raise UploadError(400, "zip 최상위 또는 바로 아래 폴더에 index.html이 있어야 합니다")


def extract_presentation(zip_bytes: bytes, dest: Path) -> None:
    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile:
        raise UploadError(400, "올바른 zip 파일이 아닙니다")

    with zf:
        entries = [(info, _safe_parts(info.filename)) for info in zf.infolist()]
        total = sum(info.file_size for info, _ in entries)
        if total > MAX_TOTAL_BYTES:
            raise UploadError(413, "압축 해제 용량이 200MB를 넘습니다")
        root = _find_root(entries)

        tmp = dest.with_name(dest.name + ".extracting")
        if tmp.exists():
            shutil.rmtree(tmp)
        tmp.mkdir(parents=True)
        for info, parts in entries:
            if info.is_dir() or parts[: len(root)] != root:
                continue
            rel = parts[len(root):]
            if not rel:
                continue
            target = tmp.joinpath(*rel)
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out)

    if dest.exists():
        shutil.rmtree(dest)
    tmp.rename(dest)
