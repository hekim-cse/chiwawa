# AI Planning DTO 계약

## 범위

이 문서는 백엔드와 AI 여행 일정 플래너 사이의 내부 DTO 계약을 정의한다.
AI 플래너는 사진 분석, 장소 메타데이터 수집, 사용자 CRUD, 일정 저장을
담당하지 않는다. 백엔드는 확정된 여행 day 조건과 확정 POI 목록을 AI에
전달하고, AI는 day별 POI 배정 결과를 반환한다.

반환된 결과는 이후 경로 최적화, 실제 시간표 생성, 빈 시간대 추천 단계로
넘길 수 있는 기반 데이터가 된다.

## 현재 계약

백엔드는 `TripPlanningRequest`를 보낸다.

| 필드 | 타입 | 규칙 |
| --- | --- | --- |
| `trip_id` | `str` | 백엔드 여행 ID |
| `timezone` | `str` | `Asia/Tokyo` 같은 유효한 IANA 타임존 |
| `days` | `list[TripPlanningDayConstraint]` | 최소 1개 이상의 여행 day |
| `pois` | `list[TripPlanningPOI]` | 사용자가 확정한 POI 목록. 빈 목록은 허용하지만 보통 AI 호출을 건너뛰는 것이 맞다. |

`TripPlanningDayConstraint`는 여행 day의 고정 조건을 나타낸다.

| 필드 | 타입 | 규칙 |
| --- | --- | --- |
| `day_index` | `int` | 1부터 시작하는 여행 일차 |
| `date` | `date` | JSON에서는 ISO 날짜 문자열 |
| `start_place` | `TripPlanningPlace` | 해당 day의 고정 출발지 |
| `start_time` | `time` | JSON에서는 `HH:MM` 시간 문자열 |
| `end_place` | `TripPlanningPlace` | 해당 day의 고정 도착지 |
| `end_time` | `time` | JSON에서는 `HH:MM` 시간 문자열 |
| `max_place_count` | `int | None` | 해당 day에 배정할 최대 POI 수 |

`TripPlanningPlace`는 출발지, 도착지, POI 위치를 표현하는 공통 장소 구조다.

| 필드 | 타입 | 규칙 |
| --- | --- | --- |
| `place_id` | `str` | 백엔드 또는 외부 장소 ID |
| `name` | `str` | 장소명 |
| `lat` | `float` | 위도, -90 이상 90 이하 |
| `lng` | `float` | 경도, -180 이상 180 이하 |

`TripPlanningPOI`는 사용자가 방문하겠다고 확정한 장소를 나타낸다.

| 필드 | 타입 | 규칙 |
| --- | --- | --- |
| `poi_id` | `str` | 서비스 내부 POI ID |
| `place_id` | `str` | Google Place ID 또는 백엔드 장소 ID |
| `name` | `str` | 장소명 |
| `lat` | `float` | 위도, -90 이상 90 이하 |
| `lng` | `float` | 경도, -180 이상 180 이하 |
| `category` | `str` | 장소 카테고리 |
| `estimated_stay_minutes` | `int` | 1분 이상의 예상 체류 시간 |
| `priority` | `int` | 사용자 우선순위, 1부터 5까지 |
| `must_visit` | `bool` | 반드시 방문해야 하는 장소인지 여부 |
| `preferred_day_index` | `int | None` | 사용자가 선호하는 1-based day 번호 |

AI는 `TripPlanningResponse`를 반환한다.

| 필드 | 타입 | 규칙 |
| --- | --- | --- |
| `trip_id` | `str` | 백엔드 여행 ID echo |
| `status` | `TripPlanningStatus` | `SUCCESS`, `PARTIAL`, `FAILED` |
| `day_plans` | `list[TripPlanningDayPlan]` | day별 POI 배정 결과 |
| `unassigned_pois` | `list[TripPlanningUnassignedPOI]` | 배정하지 못한 POI와 사유 |
| `warnings` | `list[str]` | 일정 생성 과정의 비치명 경고 |

`TripPlanningDayPlan`은 day별 배정 결과다.

| 필드 | 타입 | 규칙 |
| --- | --- | --- |
| `day_index` | `int` | 1부터 시작하는 여행 일차 |
| `date` | `date` | JSON에서는 ISO 날짜 문자열 |
| `start_place` | `TripPlanningPlace` | 해당 day의 출발지 |
| `end_place` | `TripPlanningPlace` | 해당 day의 도착지 |
| `assigned_pois` | `list[TripPlanningPOI]` | 해당 day에 배정된 POI 목록 |
| `estimated_total_stay_minutes` | `int` | 배정된 POI의 예상 체류 시간 합 |
| `assignment_reason` | `str` | 해당 day에 POI가 배정된 이유 |

`TripPlanningUnassignedPOI`는 `poi`와 `reason`으로 구성한다.

## 코드 위치

DTO 구현은 `backend/src/chiwawa_backend/schemas/ai_planning.py`에 있다.
기존 `ApiModel`을 상속하므로 모델은 frozen이고, 정의되지 않은 필드는
거부한다. 모듈은 `chiwawa_backend.schemas`에서도 export한다.

## 통합 경계

AI 플래너를 실제로 호출하려면 백엔드가 아래 좌표를 모두 확보해야 한다.

- 각 day의 출발지와 도착지 좌표
- `pois`에 담기는 모든 POI 좌표

현재 공개 `/api/v1/trips/{trip_id}/ai-plans` 흐름은 좌표가 없는 wanted place도
허용한다. 따라서 직접 AI 호출 연결은 출발지/도착지 입력과 POI 좌표 보강이
준비된 뒤에 붙이는 것이 맞다. 그 전까지 이 DTO는 향후 AI adapter가 따라야
할 안정적인 내부 계약으로 둔다.

## 이후 확장

Route Option Solver와 Timeline Builder가 붙으면 기존 배정 필드를 깨지 않고
응답에 선택 섹션을 추가한다.

```python
route_options: list[RouteOption]
timeline: list[TimelineItem]
free_time_recommendations: list[FreeTimeRecommendation]
```

처리 순서는 다음과 같이 유지한다.

1. day별 POI 배정
2. day별 경로 옵션
3. 실제 시간표
4. 빈 시간대 추천 결과
