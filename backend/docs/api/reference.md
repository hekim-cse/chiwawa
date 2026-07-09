# Chiwawa Backend API 명세

현재 FastAPI 라우터가 노출하는 HTTP API 목록입니다. 정확한 요청/응답
스키마는 실행 중인 Swagger UI와 OpenAPI JSON을 최종 기준으로 봅니다.

## 문서 확인

서버 실행 후 브라우저에서 루트 또는 Swagger UI 주소를 열면 됩니다.

```bash
uv run uvicorn chiwawa_backend.main:app --reload --host 0.0.0.0 --port 8000
```

| 문서 | URL |
| --- | --- |
| Swagger UI 바로가기 | `http://localhost:8000/` |
| Swagger UI | `http://localhost:8000/docs` |
| ReDoc | `http://localhost:8000/redoc` |
| OpenAPI JSON | `http://localhost:8000/openapi.json` |
| Health check | `http://localhost:8000/health` |

## 공통 규칙

- API prefix: `/api/v1`
- 요청/응답 본문: JSON
- 검증 실패: FastAPI 기본 `422 Unprocessable Entity`
- 존재하지 않는 리소스: `404 {"detail": "..."}`
- Google 인증 API는 환경 변수 `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`,
  `GOOGLE_REDIRECT_URI`, `JWT_SECRET_KEY` 설정에 의존합니다.
- 인증 흐름 상세는 [auth.md](./auth.md)를 봅니다.
- 백엔드 구조는 [backend.md](../architecture/backend.md)를 봅니다.

## API 목록

| Tag | Method | Status | 설명 | Path | Request | Response |
| --- | --- | --- | --- | --- | --- | --- |
| health | GET | 200 | 서버 상태 확인 | `/health` | - | `HealthResponse` |
| auth | GET | 302 | Google OAuth 로그인 URL로 이동 | `/api/v1/auth/google/login` | - | Redirect |
| auth | GET | 200 | Google OAuth callback 처리 후 JWT 발급 | `/api/v1/auth/google/callback` | query: `code` | `GoogleAuthResponse` + `access_token` |
| auth | GET | 200 | Bearer 토큰 기준 현재 사용자 확인 | `/api/v1/auth/me` | Authorization header | `{sub,email,name}` |
| trips | POST | 201 | 여행 프로젝트 생성 | `/api/v1/trips` | `TripCreateRequest` | `TripRead` |
| trips | GET | 200 | 여행 프로젝트 목록 조회 | `/api/v1/trips` | - | `TripListResponse` |
| trips | GET | 200 | 여행 프로젝트 상세 조회 | `/api/v1/trips/{trip_id}` | - | `TripRead` |
| trips | PATCH | 200 | 여행 프로젝트 수정 | `/api/v1/trips/{trip_id}` | `TripUpdateRequest` | `TripRead` |
| trips | DELETE | 204 | 여행 프로젝트 삭제 | `/api/v1/trips/{trip_id}` | - | - |
| photo-places | POST | 201 | 사진 기반 장소 후보 검색 | `/api/v1/trips/{trip_id}/photo-places/search` | `PhotoPlaceSearchRequest` | `PhotoPlaceSearchResponse` |
| photo-places | POST | 201 | 사진 장소 후보 확정 | `/api/v1/trips/{trip_id}/photo-places/{photo_search_id}/confirm` | `PhotoPlaceConfirmRequest` | `ConfirmedPhotoPlaceRead` |
| places | POST | 201 | 방문 희망 장소 등록 | `/api/v1/trips/{trip_id}/wanted-places` | `WantedPlaceCreateRequest` | `WantedPlaceRead` |
| places | GET | 200 | 방문 희망 장소 목록 조회 | `/api/v1/trips/{trip_id}/wanted-places` | - | `WantedPlaceListResponse` |
| places | PATCH | 200 | 방문 희망 장소 수정 | `/api/v1/trips/{trip_id}/wanted-places/{place_id}` | `WantedPlaceUpdateRequest` | `WantedPlaceRead` |
| places | DELETE | 204 | 방문 희망 장소 삭제 | `/api/v1/trips/{trip_id}/wanted-places/{place_id}` | - | - |
| plans | POST | 202 | AI 여행 일정 생성 요청 | `/api/v1/trips/{trip_id}/ai-plans` | `AIPlanCreateRequest` | `PlanJobRead` |
| plans | GET | 200 | AI 일정 생성 상태 조회 | `/api/v1/trips/{trip_id}/ai-plans/{plan_job_id}` | - | `PlanJobRead` |
| plans | GET | 200 | AI 생성 일정 초안 조회 | `/api/v1/trips/{trip_id}/plans/{plan_id}` | - | `PlanDraftRead` |
| plans | POST | 201 | AI 일정 초안 확정 | `/api/v1/trips/{trip_id}/plans/{plan_id}/confirm` | - | `PlanConfirmResponse` |
| plans | POST | 201 | 여행 동선 최적화 | `/api/v1/trips/{trip_id}/route-optimizations` | `RouteOptimizationRequest` | `RouteOptimizationResponse` |
| schedule | POST | 201 | 사용자 일정 등록 | `/api/v1/trips/{trip_id}/schedule-items` | `ScheduleItemCreateRequest` | `ScheduleItemRead` |
| schedule | GET | 200 | 전체 일정 조회 | `/api/v1/trips/{trip_id}/schedule` | - | `ScheduleResponse` |
| schedule | PATCH | 200 | 일정 항목 수정 | `/api/v1/trips/{trip_id}/schedule-items/{item_id}` | `ScheduleItemUpdateRequest` | `ScheduleItemRead` |
| schedule | DELETE | 204 | 일정 항목 삭제 | `/api/v1/trips/{trip_id}/schedule-items/{item_id}` | - | - |
| travel | GET | 200 | 오늘 일정 조회 | `/api/v1/trips/{trip_id}/travel/today` | - | `TodayScheduleResponse` |
| travel | POST | 201 | 빈 시간대 활동 추천 | `/api/v1/trips/{trip_id}/travel/free-time-recommendations` | `FreeTimeRecommendationRequest` | `FreeTimeRecommendationResponse` |
| travel | POST | 201 | 빈 시간 추천 일정 추가 | `/api/v1/trips/{trip_id}/travel/free-time-recommendations/{recommendation_id}/add` | - | `AddRecommendationResponse` |
| assistant | POST | 201 | 현재 위치 기반 코스 추천 | `/api/v1/trips/{trip_id}/assistant/nearby` | `NearbyRecommendationRequest` | `NearbyRecommendationResponse` |
| assistant | POST | 201 | 일정 변경/지연 재추천 | `/api/v1/trips/{trip_id}/assistant/replan` | `ReplanRequest` | `ReplanResponse` |
| memorial | POST | 201 | 여행 사진 메타데이터 등록 | `/api/v1/trips/{trip_id}/memorial/photos` | `MemorialPhotoUploadRequest` | `MemorialPhotoRead` |
| memorial | GET | 200 | 여행 사진 메타데이터 조회 | `/api/v1/trips/{trip_id}/memorial/photos` | - | `MemorialPhotoListResponse` |
| memorial | POST | 201 | 여행 기록 생성 | `/api/v1/trips/{trip_id}/memorial/generate` | `MemorialGenerateRequest` | `MemorialRecordRead` |
| memorial | GET | 200 | 여행 기록 조회 | `/api/v1/trips/{trip_id}/memorial` | - | `MemorialRecordRead` |
| memorial | PATCH | 200 | 여행 기록 수정 | `/api/v1/trips/{trip_id}/memorial` | `MemorialUpdateRequest` | `MemorialRecordRead` |

## 핵심 사용 흐름

1. `POST /api/v1/trips`로 여행 프로젝트를 생성합니다.
2. `POST /api/v1/trips/{trip_id}/wanted-places`로 방문 희망 장소를 등록합니다.
3. 선택적으로 `photo-places/search`와 `confirm`으로 사진 기반 장소를 확정합니다.
4. `POST /api/v1/trips/{trip_id}/ai-plans`로 일정 초안을 생성합니다.
5. `GET /api/v1/trips/{trip_id}/plans/{plan_id}`로 초안을 확인합니다.
6. `POST /api/v1/trips/{trip_id}/plans/{plan_id}/confirm`으로 일정을 확정합니다.
7. `POST /api/v1/trips/{trip_id}/route-optimizations`로 방문 동선을 최적화합니다.
8. 여행 중에는 `/travel`과 `/assistant` API로 빈 시간 추천, 주변 추천, 재추천을 사용합니다.
9. 여행 후에는 `/memorial/photos`와 `/memorial/generate`로 기록을 생성합니다.
