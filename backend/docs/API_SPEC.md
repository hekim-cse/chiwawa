# API 명세서

| Category | 메소드 | API | 요청 경로 |
| --- | --- | --- | --- |
| 공통 | GET | 서버 상태 확인 | `/health` |
| 여행 생성 | POST | 여행 프로젝트 생성 | `/api/v1/trips` |
| 여행 생성 | GET | 여행 프로젝트 목록 조회 | `/api/v1/trips` |
| 여행 생성 | GET | 여행 프로젝트 상세 조회 | `/api/v1/trips/{trip_id}` |
| 여행 생성 | PATCH | 여행 프로젝트 수정 | `/api/v1/trips/{trip_id}` |
| 여행 생성 | DELETE | 여행 프로젝트 삭제 | `/api/v1/trips/{trip_id}` |
| 사진 기반 장소 탐색 | POST | 사진 기반 장소 후보 검색 | `/api/v1/trips/{trip_id}/photo-places/search` |
| 사진 기반 장소 탐색 | POST | 사진 장소 후보 확정 | `/api/v1/trips/{trip_id}/photo-places/{photo_search_id}/confirm` |
| 방문 희망 장소 | POST | 방문 희망 장소 등록 | `/api/v1/trips/{trip_id}/wanted-places` |
| 방문 희망 장소 | GET | 방문 희망 장소 목록 조회 | `/api/v1/trips/{trip_id}/wanted-places` |
| 방문 희망 장소 | PATCH | 방문 희망 장소 수정 | `/api/v1/trips/{trip_id}/wanted-places/{place_id}` |
| 방문 희망 장소 | DELETE | 방문 희망 장소 삭제 | `/api/v1/trips/{trip_id}/wanted-places/{place_id}` |
| AI 일정 설계 | POST | AI 여행 일정 생성 요청 | `/api/v1/trips/{trip_id}/ai-plans` |
| AI 일정 설계 | GET | AI 일정 생성 상태 조회 | `/api/v1/trips/{trip_id}/ai-plans/{plan_job_id}` |
| AI 일정 설계 | GET | AI 생성 일정 초안 조회 | `/api/v1/trips/{trip_id}/plans/{plan_id}` |
| AI 일정 설계 | POST | AI 일정 초안 확정 | `/api/v1/trips/{trip_id}/plans/{plan_id}/confirm` |
| AI 일정 설계 | POST | 여행 동선 최적화 | `/api/v1/trips/{trip_id}/route-optimizations` |
| 일정 등록 | POST | 사용자 일정 등록 | `/api/v1/trips/{trip_id}/schedule-items` |
| 일정 등록 | GET | 전체 일정 조회 | `/api/v1/trips/{trip_id}/schedule` |
| 일정 등록 | PATCH | 일정 항목 수정 | `/api/v1/trips/{trip_id}/schedule-items/{item_id}` |
| 일정 등록 | DELETE | 일정 항목 삭제 | `/api/v1/trips/{trip_id}/schedule-items/{item_id}` |
| 여행 중 | GET | 오늘 일정 조회 | `/api/v1/trips/{trip_id}/travel/today` |
| 여행 중 | POST | 빈 시간대 활동 추천 | `/api/v1/trips/{trip_id}/travel/free-time-recommendations` |
| 여행 중 | POST | 빈 시간 추천 일정 추가 | `/api/v1/trips/{trip_id}/travel/free-time-recommendations/{recommendation_id}/add` |
| 여행 도우미 | POST | 현재 위치 기반 코스 추천 | `/api/v1/trips/{trip_id}/assistant/nearby` |
| 여행 도우미 | POST | 일정 변경/지연 재추천 | `/api/v1/trips/{trip_id}/assistant/replan` |
| Memorial | POST | 여행 사진 업로드 | `/api/v1/trips/{trip_id}/memorial/photos` |
| Memorial | GET | 여행 사진 메타데이터 조회 | `/api/v1/trips/{trip_id}/memorial/photos` |
| Memorial | POST | 여행 기록 생성 | `/api/v1/trips/{trip_id}/memorial/generate` |
| Memorial | GET | 여행 기록 조회 | `/api/v1/trips/{trip_id}/memorial` |
| Memorial | PATCH | 여행 기록 수정 | `/api/v1/trips/{trip_id}/memorial` |

