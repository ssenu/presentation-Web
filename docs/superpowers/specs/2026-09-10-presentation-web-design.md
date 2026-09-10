# 발표자료 웹 (presentation-Web) 설계

날짜: 2026-09-10

## 목적

html로 만든 발표자료를 웹에 올려 두고, 비밀번호 하나로 다른 컴퓨터에서도 접속해 열람한다.
발표자료는 웹에서 zip으로 업로드하며, 서버가 목록을 자동으로 관리한다.

## 요구사항

- 비밀번호 1개로 로그인. 통과하면 열람과 관리 모두 가능.
- 흰 바탕 가운데 세로 목록. 클릭하면 발표자료가 새 탭에서 열린다.
- 발표자료는 `index.html` + 보조 파일(이미지, css 등)로 구성된 폴더. zip으로 업로드.
- 관리 기능: 업로드, 삭제, 제목 변경, 같은 제목으로 덮어쓰기, 순서 변경(드래그), 카테고리 분류.
- 내 서버에 Docker 컨테이너 하나로 배포. 자료는 호스트 볼륨에 저장.

## 기술 스택

- 백엔드: Python 3.12, FastAPI, uvicorn
- 프론트엔드: Vue 3 + Vite (빌드 산출물을 FastAPI가 정적 서빙)
- 배포: Dockerfile(멀티스테이지) + docker-compose.yml

## 디렉터리 구조

```
presentation-Web/
├─ backend/
│  ├─ app/
│  │  ├─ main.py        FastAPI 앱, 라우터 등록, 정적 서빙
│  │  ├─ auth.py        비밀번호 검증, 서명 쿠키 발급/검사
│  │  ├─ store.py       index.json 읽기/쓰기, 항목 CRUD, 순서
│  │  └─ uploads.py     zip 검증 및 압축 해제
│  ├─ tests/
│  └─ requirements.txt
├─ frontend/
│  ├─ src/
│  │  ├─ App.vue        로그인 여부에 따라 Login / List 표시
│  │  ├─ Login.vue
│  │  ├─ List.vue       목록 + 편집 모드
│  │  └─ api.js         fetch 래퍼
│  ├─ index.html, vite.config.js, package.json
├─ data/                Docker 볼륨 (레포에는 .gitkeep만)
│  ├─ presentations/<slug>/index.html ...
│  └─ index.json
├─ Dockerfile
├─ docker-compose.yml
└─ .env.example
```

## 인증

- 환경변수 `APP_PASSWORD`(필수), `SECRET_KEY`(쿠키 서명용, 필수).
- `POST /api/login` 에 `{password}` 를 보내 일치하면 `session` 쿠키 발급. HttpOnly, SameSite=Lax, 30일.
- 쿠키 값은 `itsdangerous` 서명 토큰. 서버는 비밀번호를 저장하지 않는다.
- `/api/*`(login 제외)와 `/p/*`는 쿠키 검사. 실패 시 401.
- `POST /api/logout` 으로 쿠키 삭제.

## 저장 구조

`data/index.json`:

```json
{
  "items": [
    { "slug": "2026-q3-review", "title": "2026 Q3 리뷰", "category": "회사", "order": 0 }
  ]
}
```

- `slug`: 제목에서 만든 URL용 문자열(한글은 유지, 공백은 `-`, 파일시스템 금지문자 제거). 충돌 시 `-2`, `-3` 접미.
- `category`: 빈 문자열이면 미분류.
- `order`: 전체 목록 내 정수. 카테고리는 별도 테이블 없이 항목의 `category` 값으로만 존재한다.
- 파일 쓰기는 임시 파일에 쓴 뒤 rename 하여 원자적으로 교체한다.

`data/presentations/<slug>/` 에 zip 내용을 푼다. 진입점은 `index.html`.

## 업로드 규칙

- `POST /api/items` multipart: `file`(zip), `title`(선택, 없으면 zip 파일명), `category`(선택).
- zip 안에서 `index.html`을 찾는다. 최상위에 있으면 그대로, 폴더 하나로 감싸져 있으면(`xxx/index.html`) 그 폴더를 루트로 본다. 둘 다 아니면 400.
- 각 엔트리 경로를 정규화해 `..`나 절대경로가 있으면 400.
- 압축 해제 용량 상한 200MB. 초과 시 413.
- 같은 `title`이 이미 있으면 덮어쓰기: 기존 폴더를 삭제하고 새로 푼다. slug, category, order는 유지.

## API

| 메서드 | 경로 | 설명 |
|---|---|---|
| POST | /api/login | `{password}` → 쿠키 |
| POST | /api/logout | 쿠키 삭제 |
| GET | /api/me | 로그인 여부 확인(200/401) |
| GET | /api/items | 항목 목록, `order` 오름차순 |
| POST | /api/items | zip 업로드(신규 또는 덮어쓰기) |
| PATCH | /api/items/{slug} | `{title?, category?}` 수정. 제목 변경 시 slug는 유지 |
| DELETE | /api/items/{slug} | 항목과 폴더 삭제 |
| PUT | /api/items/order | `{slugs: [...]}` 순서 일괄 저장 |
| GET | /p/{slug}/ | 해당 발표자료의 index.html |
| GET | /p/{slug}/{path} | 보조 파일 |

에러는 `{detail: "..."}` JSON.

## 화면

**로그인**: 흰 배경, 세로·가로 가운데 정렬된 입력창과 버튼 하나. 틀리면 입력창 아래 빨간 한 줄.

**목록**: 흰 배경, 가로 최대 640px 가운데 정렬. 카테고리마다 소제목을 두고 그 아래 항목을 세로로 나열. 미분류는 소제목 없이 맨 아래. 항목 클릭 시 `/p/<slug>/` 를 새 탭으로 연다.

**편집 모드**: 우상단 "편집" 토글.
- 상단에 zip 드롭 영역 + 제목/카테고리 입력.
- 각 항목에 드래그 핸들, 제목 인라인 수정, 카테고리 입력(datalist로 기존 카테고리 제안), 삭제 버튼(브라우저 confirm).
- 드래그 정렬은 HTML5 drag & drop으로 직접 구현. 놓으면 즉시 `PUT /api/items/order`.
- 카테고리는 항목의 값을 바꾸는 것으로 이동. 항목이 없는 카테고리는 자동으로 사라진다.

## Docker

- Dockerfile: 1단계 `node:20-alpine`에서 `npm ci && npm run build`, 2단계 `python:3.12-slim`에 backend와 `frontend/dist` 복사, `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
- docker-compose.yml: 포트 `8000:8000`, 볼륨 `./data:/data`, `env_file: .env`.
- 환경변수 `DATA_DIR`(기본 `/data`), `APP_PASSWORD`, `SECRET_KEY`.

## 테스트

백엔드 pytest(TestClient, 임시 DATA_DIR):
- 로그인 성공/실패, 미로그인 접근 401
- 업로드 정상(최상위 index.html, 폴더로 감싸진 index.html), index.html 없음 400, 경로 탈출 400
- 같은 제목 업로드 시 덮어쓰기와 slug 유지
- 제목/카테고리 수정, 삭제 후 폴더 제거, 순서 저장
- `/p/{slug}/` 로 index.html 서빙

프론트는 수동 확인.

## 범위 밖

- 다중 사용자, 권한 구분
- 발표자료 편집기
- HTTPS 종단(리버스 프록시에 맡김)
