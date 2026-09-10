# presentation-Web

html로 만든 발표자료를 비밀번호 하나로 보호해서 웹에 올려 두는 작은 서비스.
zip으로 업로드하면 목록에 나타나고, 클릭하면 발표자료가 새 탭에서 열린다.

## 실행 (Docker)

```bash
cp .env.example .env      # APP_PASSWORD, SECRET_KEY 수정
docker compose up -d --build
```

`http://<서버주소>:8000` 접속. 발표자료와 메타데이터는 `./data` 에 저장된다.

## 사용법

1. 비밀번호로 로그인
2. 우상단 **편집** 클릭
3. `index.html`이 들어 있는 zip 파일을 올린다 (폴더 하나로 감싸져 있어도 됨)
4. 편집 모드에서 제목·카테고리 수정, 드래그로 순서 변경, 삭제 가능
5. 같은 제목으로 다시 올리면 덮어쓴다

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
