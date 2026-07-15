# AI Planning DTO 계약

이 문서는 백엔드와 AI planner adapter 사이의 내부 wire 계약입니다. 백엔드는
여행 day 조건과 확정 POI를 전달하고, AI는 day별 배정과 선택적 route/timeline을
반환합니다. 실제 모델 호출 구현은 이 저장소의 범위가 아닙니다.

## 요청

`TripPlanningRequest`

| 필드 | 타입 | 규칙 |
| --- | --- | --- |
| `trip_id` | string | 비어 있지 않음 |
| `timezone` | string | 유효한 IANA timezone, 기본 `Asia/Tokyo` |
| `days` | day[] | 최소 1개 |
| `pois` | POI[] | 최소 1개 |

day는 `day_index`, `date`, `start_place`, `start_time`, `end_place`, `end_time`,
선택적 `max_place_count`로 구성됩니다.

- `day_index`는 1부터 중복 없이 연속이어야 합니다.
- date는 중복 없이 day index 순으로 증가해야 합니다.
- time wire 형식은 정확히 offset 없는 `HH:MM`이며 `start_time < end_time`입니다.
- place는 `place_id`, `name`, `lat`, `lng`를 모두 포함합니다.

POI 필드는 `poi_id`, `place_id`, `name`, `lat`, `lng`, `category`,
`estimated_stay_minutes`, `priority`, `must_visit`, 선택적
`preferred_day_index`입니다. 선호 day는 요청의 실제 day index를 참조해야 합니다.

`category` 허용값은 다음과 같습니다.

```text
TOURIST_ATTRACTION, RESTAURANT, CAFE, SHOPPING, ACTIVITY, HOTEL, ETC
```

## 응답

`TripPlanningResponse`

| 필드 | 타입 | 규칙 |
| --- | --- | --- |
| `trip_id` | string | 요청 trip ID echo |
| `status` | enum | `SUCCESS`, `PARTIAL_SUCCESS`, `FAILED` |
| `day_plans` | day plan[] | 필수, 빈 목록은 허용 |
| `unassigned_pois` | item[] | 기본 빈 목록 |
| `warnings` | string[] | 기본 빈 목록 |

day plan은 입력 day와 같은 `day_index`, `date`, 시작·종료 place를 가지며
`assigned_pois`, `estimated_total_stay_minutes`, `assignment_reason`, 선택적
`route_options`를 포함합니다. 각 route option의 `day_index`는 부모 day와 같아야
합니다.

route option은 아래 계약입니다.

- `travel_mode`: `WALK`, `DRIVE`, `TRANSIT`
- `ordered_stops`: stop type `START`, `POI`, `END`와 장소·좌표
- `route_legs`: origin/destination place ID와 0 이상의 이동 분
- `missing_segments`, `warnings`: 기본 빈 목록
- `timeline`: 선택값이며 route option과 day index/travel mode가 같아야 함

timeline은 계획·실제 종료 시각, 총 이동·체류 분, `timeline_stops`, 종료 초과 여부,
warnings를 포함합니다. timeline stop은 stop type, 장소, 도착·출발 시각,
0 이상의 체류 분으로 구성됩니다.

## 처리 순서와 경계

```text
day constraint + POI assignment
  -> route options
  -> selected route timeline
  -> backend persistence/confirmation
```

모든 DTO는 `ApiModel`을 상속하므로 frozen이고 알 수 없는 필드를 거부합니다.
구현 정본은 `src/chiwawa_backend/schemas/ai_planning.py`입니다. 백엔드의 공개
`/api/v1/trips/{trip_id}/ai-plans`는 현재 결정적 휴리스틱이며 이 DTO를 실제
AI provider와 연결하려면 모든 출발지·도착지·POI 좌표를 먼저 확보해야 합니다.
