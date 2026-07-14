# Chiwawa Backend

일본 자유여행 일정 추천·관리 흐름을 검증하기 위한 FastAPI 개발
프로토타입입니다. 이 디렉터리만으로 실행, 테스트, wheel 빌드가 가능합니다.

## 현재 구현 범위

- 여행, 방문 희망 장소, 일정, 여행 기록 API
- Google OAuth 로그인과 8시간 JWT 발급
- 오늘 일정, 빈 시간 추천, 주변 추천, 지연 재계획
- Swagger UI, ReDoc, OpenAPI JSON
- Pydantic 요청 검증과 서비스 계층 도메인 검증

현재 아래 기능은 외부 공급자와 연결되지 않은 모의 구현입니다.

- 사진 기반 장소 후보 검색
- AI 일정 초안 생성
- 방문 동선 최적화
- 현재 위치 기반 주변 추천
- 빈 시간 활동 추천

생성 ID와 시각을 제외한 핵심 후보·추천 내용은 같은 입력에 같은 규칙을 적용하는
시연용 휴리스틱이며, 실제 사진 인식, 지도 경로 계산, 장소 검색, AI 모델 호출을
의미하지 않습니다.

## 개발 단계의 저장·인증 범위

- 여행·장소·일정·추천·기록은 `AppState` 메모리에 저장되어 서버 재시작 시
  초기화됩니다.
- ID는 프로세스 내 숫자 카운터가 아닌 UUID를 사용합니다.
- Google 사용자와 회원 단위 Memorial 사진 메타데이터는 SQLite
  `data/google_auth.db`에 저장됩니다. 이 런타임 DB는 Git에 포함하지 않으며
  wheel에 포함된 패키지 SQL 마이그레이션으로 자동 초기화됩니다.
- OAuth `state`는 서버 메모리에서 1회 검증되고 같은 브라우저의 HttpOnly
  쿠키와 함께 결합됩니다.
- 현재 Bearer 인증이 필수인 경로는 `GET /api/v1/auth/me`와 회원 단위
  Memorial API(`/api/v1/memorial/*`)입니다.
- 여행 관련 API는 프론트엔드 연동용 프로토타입 계약을 유지하기 위해 현재
  공개 상태입니다. 공유 개발 서버나 외부 배포 전에는 사용자 소유권과
  인증 의존성을 추가해야 합니다.

## 기술 스택

- Python 3.13+
- FastAPI, Pydantic v2, pydantic-settings
- SQLite, PyJWT, HTTPX
- uv, pytest, Ruff, basedpyright

## 실행

```bash
uv sync --frozen
uv run uvicorn chiwawa_backend.main:app --reload --no-access-log --host 127.0.0.1 --port 8000
```

또는 `make run`을 사용할 수 있습니다. 인증 API를 테스트하려면
[`.env.example`](./.env.example)을 복사해 `.env`를 만들고 실제 개발용 값을
설정합니다. 인증 설정이 없어도 상태 확인, 문서, 여행 프로토타입 API는
실행됩니다. 기본 실행은 인증 없는 프로토타입 API가 외부에 노출되지 않도록
로컬 호스트에만 바인딩합니다.

| 문서/상태 | URL |
| --- | --- |
| Swagger UI 바로가기 | `http://localhost:8000/` |
| Swagger UI | `http://localhost:8000/docs` |
| ReDoc | `http://localhost:8000/redoc` |
| OpenAPI JSON | `http://localhost:8000/openapi.json` |
| Health check | `http://localhost:8000/health` |

## 품질 검사

```bash
uv run ruff format --check .
uv run ruff check .
uv run basedpyright
uv run pytest
uv build --wheel
```

앞의 네 검사는 `make check`로 한 번에 실행할 수 있습니다.

## 주요 흐름

1. `POST /api/v1/trips`로 여행을 생성합니다.
2. `POST /api/v1/trips/{trip_id}/wanted-places`로 장소를 등록합니다.
3. `POST /api/v1/trips/{trip_id}/ai-plans`로 시간창 안의 모의 일정을 만듭니다.
4. `GET /api/v1/trips/{trip_id}/plans/{plan_id}`로 초안을 확인합니다.
5. `POST /api/v1/trips/{trip_id}/plans/{plan_id}/confirm`으로 일정을 확정합니다.
   같은 계획을 다시 확정해도 일정 항목은 중복 생성되지 않습니다.
6. 여행 중에는 `/travel`과 `/assistant` API로 추천과 재계획을 사용합니다.
7. 여행 후에는 `/memorial/photos`와 `/memorial/generate`로 기록을 만듭니다.

현재 여행 기간은 최대 31일이며 일정 시각은 오프셋 없는 일본 현지 시각으로
입력합니다. `/travel/today`의 기준 시간대는 `Asia/Tokyo`입니다.

문서 인덱스는 [`docs/README.md`](./docs/README.md), 전체 경로 목록은
[`docs/api/reference.md`](./docs/api/reference.md), 인증 상세는
[`docs/api/auth.md`](./docs/api/auth.md)에서 확인합니다.
