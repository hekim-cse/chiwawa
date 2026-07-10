# 백엔드 구조

현재 백엔드는 FastAPI 기반 인메모리 MVP이며, 기능별 라우터가
`src/chiwawa_backend/routers/`에 분리되어 있다.

## 모듈 구조

| 영역 | 경로 | 역할 |
| --- | --- | --- |
| 앱 엔트리 | `src/chiwawa_backend/main.py` | FastAPI 앱 생성, 라우터 등록, 예외 핸들러, Swagger 진입점 |
| 라우터 | `src/chiwawa_backend/routers/` | HTTP 경로, 요청 DTO, 응답 DTO 연결 |
| 스키마 | `src/chiwawa_backend/schemas/` | Pydantic v2 API 요청/응답 모델 |
| 서비스 | `src/chiwawa_backend/services/` | 여행, 장소, 일정, 추천, 기록 비즈니스 로직 |
| 상태 저장소 | `src/chiwawa_backend/state.py` | 시연용 인메모리 저장소 |
| 인증 저장소 | `data/google_auth.db`, `sql/001_google_users.sql` | Google OAuth 사용자 저장 SQLite 스키마 |

## 요청 처리 흐름

```text
HTTP request
  -> router
  -> Pydantic request schema
  -> service
  -> AppState or auth storage
  -> Pydantic response schema
  -> HTTP response
```

## 라우터 구성

| 라우터 | Prefix | 역할 |
| --- | --- | --- |
| `health.py` | `/health` | 서버 상태 확인 |
| `auth.py` | `/api/v1/auth` | Google OAuth, JWT 사용자 확인 |
| `trips.py` | `/api/v1/trips` | 여행 프로젝트 CRUD |
| `photo_places.py` | `/api/v1/trips/{trip_id}/photo-places` | 사진 기반 장소 후보 검색과 확정 |
| `wanted_places.py` | `/api/v1/trips/{trip_id}/wanted-places` | 방문 희망 장소 CRUD |
| `plans.py` | `/api/v1/trips/{trip_id}` | AI 일정 생성, 일정 확정, 동선 최적화 |
| `schedule.py` | `/api/v1/trips/{trip_id}` | 일정 항목 CRUD |
| `travel.py` | `/api/v1/trips/{trip_id}/travel` | 여행 중 일정 조회와 빈 시간 추천 |
| `assistant.py` | `/api/v1/trips/{trip_id}/assistant` | 주변 추천과 재추천 |
| `memorial.py` | `/api/v1/trips/{trip_id}/memorial` | 여행 사진 메타데이터와 기록 생성 |

## 실행 표면

- Swagger UI 바로가기: `http://localhost:8000/`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## 확장 기준

- 라우터는 HTTP 계약만 다루고 비즈니스 로직은 서비스에 둔다.
- 요청/응답 모델은 `schemas/`에 두고 라우터 함수의 타입으로 노출한다.
- 현재 `AppState`는 MVP 저장소이므로 실제 DB 도입 시 repository/ORM 계층으로 교체한다.
- 라우터 계약을 바꾸는 변경은 [api/reference.md](../api/reference.md)와 Swagger 테스트를 같이 갱신한다.
