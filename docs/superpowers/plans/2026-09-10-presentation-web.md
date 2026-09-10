# 발표자료 웹 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 비밀번호 하나로 보호되는 html 발표자료 목록 웹을 FastAPI + Vue + Docker로 만든다.

**Architecture:** FastAPI 단일 프로세스가 API, 인증 쿠키, 발표자료 정적 파일, 빌드된 Vue 앱을 모두 서빙한다. 메타데이터는 `data/index.json` 하나, 자료는 `data/presentations/<slug>/`. Docker 멀티스테이지로 Vue를 빌드해 python 이미지에 넣는다.

**Tech Stack:** Python 3.12, FastAPI, uvicorn, itsdangerous, python-multipart, pytest, httpx / Vue 3, Vite / Docker, docker compose

## Global Constraints

- 환경변수: `APP_PASSWORD`, `SECRET_KEY` 필수, `DATA_DIR` 기본 `/data`
- 쿠키 이름 `session`, HttpOnly, SameSite=Lax, 30일
- 압축 해제 상한 200MB → 413
- zip 경로 탈출 → 400, index.html 없음 → 400
- 스펙: `docs/superpowers/specs/2026-09-10-presentation-web-design.md`

---

### Task 1: 백엔드 뼈대 + 인증

**Files:** `backend/requirements.txt`, `backend/app/__init__.py`, `backend/app/config.py`, `backend/app/auth.py`, `backend/app/main.py`, `backend/tests/conftest.py`, `backend/tests/test_auth.py`, `.gitignore`

**Interfaces (Produces):**
- `config.Settings` (data_dir: Path, app_password: str, secret_key: str), `config.get_settings()`
- `auth.make_token(secret) -> str`, `auth.verify_token(secret, token) -> bool`
- `auth.require_login` FastAPI dependency (Cookie `session` 검사, 실패 시 401)
- 라우트 `POST /api/login`, `POST /api/logout`, `GET /api/me`

**Tests:** 로그인 성공 시 쿠키 세팅 + `/api/me` 200, 틀린 비밀번호 401, 쿠키 없이 `/api/me` 401, 로그아웃 후 401.

conftest: `tmp_path`를 `DATA_DIR`, `APP_PASSWORD=pw`, `SECRET_KEY=s`로 환경변수 설정 후 `app` import, `TestClient` 반환.

- [ ] 테스트 작성 → 실패 확인 → 구현 → 통과 → 커밋 `feat: backend auth`

### Task 2: 메타데이터 저장소 (store.py)

**Files:** `backend/app/store.py`, `backend/tests/test_store.py`

**Interfaces (Produces):**
- `Item` pydantic 모델: slug, title, category(str, 기본 ""), order(int)
- `Store(data_dir)`: `list() -> list[Item]` (order 순), `get(slug)`, `find_by_title(title)`, `add(title, category) -> Item` (slug 생성·충돌 회피, order = max+1), `update(slug, title=None, category=None) -> Item`, `remove(slug)`, `reorder(slugs: list[str])`, `presentations_dir` 프로퍼티, `item_dir(slug)`
- `slugify(title) -> str`: 소문자화하지 않음, 공백→`-`, `/\:*?"<>|` 및 `.`으로 시작 금지 제거, 빈 값이면 `item`
- 저장은 임시파일 후 `os.replace`

**Tests:** 빈 저장소 list == [], add 후 list, slug 충돌 시 `-2`, update 제목/카테고리, remove, reorder 후 order 재부여, index.json 파일 존재.

- [ ] 커밋 `feat: item store`

### Task 3: zip 업로드 처리 (uploads.py)

**Files:** `backend/app/uploads.py`, `backend/tests/test_uploads.py`

**Interfaces (Produces):**
- `extract_presentation(zip_bytes: bytes, dest: Path) -> None`
- 예외: `UploadError(status_code, detail)`; 400(index.html 없음, 경로 탈출, 잘못된 zip), 413(200MB 초과)
- 루트 판정: `index.html` 최상위 → 그대로; 아니면 최상위 디렉터리가 하나뿐이고 그 아래 `index.html` → 그 디렉터리를 루트로. 그 외 400.
- dest가 이미 있으면 삭제 후 새로 생성

**Tests:** 최상위 index.html, 폴더로 감싼 index.html, index.html 없음, `../evil` 엔트리, 절대경로 엔트리, 기존 dest 교체, 용량 초과(entry file_size 합으로 판단, 실제 큰 파일 대신 monkeypatch 상한).

- [ ] 커밋 `feat: zip extraction`

### Task 4: 항목 API + 발표자료 서빙

**Files:** `backend/app/items.py` (APIRouter), `backend/app/main.py` 수정, `backend/tests/test_items.py`

**Routes:** `GET /api/items`, `POST /api/items` (multipart file/title/category), `PATCH /api/items/{slug}`, `DELETE /api/items/{slug}`, `PUT /api/items/order`, `GET /p/{slug}/{path:path}` (path 빈 값이면 index.html, `..` 차단, 없는 파일 404). 모두 `require_login`.

**Tests:** 미로그인 401, 업로드 후 목록에 표시 + `/p/slug/`가 html 반환, 제목 없이 업로드 시 zip 파일명(확장자 제거), 같은 제목 재업로드 시 slug 유지 + 내용 교체, PATCH, DELETE 후 폴더 삭제, order 저장, `/p/slug/../x` 404.

- [ ] 커밋 `feat: items api`

### Task 5: Vue 프론트엔드

**Files:** `frontend/package.json`, `frontend/vite.config.js` (dev 프록시 `/api`, `/p` → 8000), `frontend/index.html`, `frontend/src/main.js`, `frontend/src/api.js`, `frontend/src/App.vue`, `frontend/src/Login.vue`, `frontend/src/List.vue`, `frontend/src/style.css`

**동작:** App이 마운트 시 `/api/me` 확인 → Login 또는 List. List는 카테고리별 그룹, 편집 토글, 업로드 폼, 인라인 제목/카테고리 수정, 삭제 confirm, HTML5 드래그 정렬 후 `PUT /api/items/order`.

- [ ] `npm run build` 성공 확인, 커밋 `feat: vue frontend`

### Task 6: main.py에서 SPA 서빙 + Docker

**Files:** `backend/app/main.py` 수정 (`frontend/dist` 존재 시 `/assets` 마운트, 나머지 경로는 index.html 반환), `Dockerfile`, `docker-compose.yml`, `.env.example`, `data/.gitkeep`, `README.md`

- [ ] `docker compose build` 성공, 컨테이너 기동 후 로그인·업로드 확인, 커밋 `feat: docker packaging`
