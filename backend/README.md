# Chiwawa Backend

AI 기반 일본 자유여행 일정 추천 및 관리 서비스를 위한 FastAPI 백엔드입니다.
프로젝트 계획서와 `docs/api/reference.md`를 기준으로 여행 생성, 사진 기반
장소 탐색, AI 일정 초안, 일정 확정, 여행 중 추천, 여행 기록 생성 흐름을
하나의 API 파이프라인으로 연결합니다.

## 구현 범위

- 서버 상태 확인: `GET /health`
- 여행 프로젝트 CRUD: `/api/v1/trips`
- 사진 기반 장소 후보 검색 및 확정
- 방문 희망 장소 CRUD
- AI 일정 생성 요청, 상태 조회, 초안 조회, 확정
- 방문 장소 기반 동선 최적화
- 사용자 일정 CRUD 및 전체 일정 조회
- 오늘 일정, 빈 시간 추천, 추천 일정 추가
- 현재 위치 기반 주변 추천 및 지연/변경 재추천
- 여행 사진 메타데이터 업로드, 여행 기록 생성/조회/수정

현재 버전은 프론트엔드 연동과 시연을 위한 인메모리 저장소 기반 MVP입니다.
외부 지도, 사진 인식, AI 모델 연동 지점은 서비스 계층에 모아 두어 교체할 수
있습니다.

## 기술 스택

- Python 3.13+
- FastAPI
- Pydantic v2
- Uvicorn
- uv
- pytest, ruff, basedpyright

## 실행

```bash
uv sync
uv run uvicorn chiwawa_backend.main:app --reload --host 0.0.0.0 --port 8000
```

또는 다음 명령을 사용할 수 있습니다.

```bash
make run
```

브라우저에서 다음 문서를 확인할 수 있습니다.

- Swagger UI 바로가기: `http://localhost:8000/`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`
- Health check: `http://localhost:8000/health`

## 품질 파이프라인

```bash
uv run ruff format --check .
uv run ruff check .
uv run basedpyright
uv run pytest
```

동일한 검증은 다음 명령으로 한 번에 실행할 수 있습니다.

```bash
make check
```

## 주요 흐름

1. `POST /api/v1/trips`로 여행 프로젝트를 생성합니다.
2. `POST /api/v1/trips/{trip_id}/wanted-places`로 방문 희망 장소를 등록합니다.
3. `POST /api/v1/trips/{trip_id}/photo-places/search`로 사진 기반 장소 후보를 받습니다.
4. `POST /api/v1/trips/{trip_id}/photo-places/{photo_search_id}/confirm`으로 후보를 확정합니다.
5. `POST /api/v1/trips/{trip_id}/ai-plans`로 일정 초안을 생성합니다.
6. `GET /api/v1/trips/{trip_id}/plans/{plan_id}`로 초안을 확인합니다.
7. `POST /api/v1/trips/{trip_id}/plans/{plan_id}/confirm`으로 일정을 확정합니다.
8. 여행 중에는 `/travel`과 `/assistant` API로 빈 시간 추천, 주변 추천, 재추천을 사용합니다.
9. 여행 후에는 `/memorial/photos`와 `/memorial/generate`로 기록을 생성합니다.

## 개발 메모

- 저장소는 `src/chiwawa_backend/state.py`의 `AppState` 인스턴스에 보관됩니다.
- API 라우터는 `src/chiwawa_backend/routers/`에 기능별로 분리되어 있습니다.
- 문서 인덱스는 `docs/README.md`에서 확인합니다.
- 최신 API 명세는 `docs/api/reference.md`에서 관리합니다.
- 추천과 일정 생성 로직은 `src/chiwawa_backend/services/`에 모여 있습니다.
- 실제 DB 도입 시 `AppState`를 repository/ORM 계층으로 교체하면 라우터 계약은 유지됩니다.
