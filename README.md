# presentation-Web

html로 만든 발표자료를 비밀번호 하나로 보호해서 웹에 올려 두는 작은 서비스.
zip으로 업로드하면 목록에 나타나고, 클릭하면 발표자료가 새 탭에서 열린다.

## 실행 (Docker)

```bash
cp .env.example .env      # APP_PASSWORD, SECRET_KEY 수정
docker compose up -d --build
```

`.env`가 없어도 뜬다. 그때는 비밀번호가 `password`이고, 서명 키는 `data/secret_key`에 자동 생성되어 재시작 후에도 유지된다.
로그에 `APP_PASSWORD가 설정되지 않아` 경고가 보이면 `.env`가 컨테이너에 전달되지 않은 것이다. `.env`가 `docker-compose.yml`과 같은 폴더에 있는지, 줄 형식이 `APP_PASSWORD=값` 인지 확인하고 `docker compose up -d --force-recreate` 로 다시 띄운다.

컨테이너는 `127.0.0.1:${HOST_PORT:-8080}` 에만 바인딩된다. 같은 서버에서는 `http://127.0.0.1:8080` 으로 접속하고, 외부 공개는 nginx 같은 리버스 프록시로 이 주소를 넘긴다. 발표자료와 메타데이터는 `./data` 에 저장된다.

## 사용법

1. 비밀번호로 로그인
2. html 파일 하나, 또는 `index.html`이 들어 있는 zip(이미지 등 보조 파일 포함, 폴더 하나로 감싸져 있어도 됨)을 화면 어디든 끌어다 놓으면 업로드된다. 제목은 파일명.
3. 항목 오른쪽에 업로드 일시가 보이고, 마우스를 올리면 **수정**(제목·카테고리)과 **삭제**로 바뀐다
4. 항목을 끌어서 순서를 바꾸고, 다른 카테고리의 항목이나 카테고리 제목 위에 놓으면 그 카테고리로 이동한다
5. 목록 아래 **+ 카테고리 추가**로 빈 카테고리를 만든다. 카테고리 이름을 누르면 접거나 펼치고(접힘 상태는 브라우저에 저장), 이름에 마우스를 올리면 **수정**·**삭제**가 나타난다. 삭제하면 안에 있던 파일은 카테고리 없음으로 옮겨진다
6. 같은 제목으로 다시 올리면 덮어쓴다. 올리는 동안 화면 위에 진행률이 표시된다

로그인은 IP당 1분에 5회까지 시도할 수 있고, 틀리면 응답이 1초 지연된다. 리버스 프록시 뒤에서는 `X-Forwarded-For` 헤더의 첫 주소를 IP로 본다. 업로드 시각은 `TZ` 환경변수(기본 `Asia/Seoul`)를 따른다.

## 개발

```bash
# 백엔드
cd backend
python -m venv .venv && .venv/Scripts/pip install -r requirements-dev.txt
set APP_PASSWORD=pw && set SECRET_KEY=dev && set DATA_DIR=../data
.venv/Scripts/uvicorn app.main:app --reload
.venv/Scripts/python -m pytest

# 프론트엔드 (별도 터미널, /api 와 /p 는 8000으로 프록시)
cd frontend
npm install && npm run dev
```

## 구조

- `backend/app/main.py` 앱 진입점, 로그인, SPA 서빙
- `backend/app/items.py` 항목 API와 `/p/<slug>/` 발표자료 서빙
- `backend/app/store.py` `data/index.json` 메타데이터
- `backend/app/uploads.py` zip 검증과 압축 해제
- `frontend/src/` Vue 3 (Login, List)
- `docs/superpowers/specs/` 설계 문서
