# 🧱 Route Planner Domain

Route Planner가 사용하는 공통 데이터 구조와 백엔드 사이의 요청·응답 DTO를 정의합니다.

이 디렉터리는 경로를 직접 계산하지 않습니다.
대신 Application, Provider, Solver가 공유하는 **데이터 계약과 기본 검증 규칙**을 담당합니다.

> 상위 문서: [Route Planner](../README.md)

<br>

## 📚 목차

1. [🎯 디렉터리 역할](#-디렉터리-역할)
2. [📁 파일 구성](#-파일-구성)
3. [🚘 공통 경로 모델](#-공통-경로-모델)
4. [📥 일정 생성 요청 DTO](#-일정-생성-요청-dto)
5. [📅 일자 배정 결과 DTO](#-일자-배정-결과-dto)
6. [🛣️ Route Option DTO](#-route-option-dto)
7. [⏱️ Timeline DTO](#-timeline-dto)
8. [📤 최종 응답 DTO](#-최종-응답-dto)
9. [✅ 검증 규칙](#-검증-규칙)
10. [🔒 도메인 불변조건](#-도메인-불변조건)
11. [⚠️ 현재 모델의 주의사항](#-현재-모델의-주의사항)
12. [🔗 관련 문서](#-관련-문서)

<br>

---

## 🎯 디렉터리 역할

`ai/route_planner/domain`은 다음 책임을 가집니다.

- 이동수단 Enum 정의
- Provider 이동시간 Matrix 모델 정의
- 장소와 POI DTO 정의
- 여행 일자 제약 DTO 정의
- 일정 최적화 요청 DTO 정의
- 날짜별 배정 결과 DTO 정의
- Route Stop과 Route Leg DTO 정의
- Route Option DTO 정의
- Timeline DTO 정의
- 최종 일정 최적화 응답 DTO 정의
- DTO 생성 단계의 기본 입력 검증

도메인 모델은 Solver 구현과 외부 Provider 구현 사이의 공통 계약으로 사용됩니다.

```text
Backend Request
→ TripPlanningRequestDTO
→ Application / Solver / Provider
→ TripPlanningResponseDTO
→ Backend Response
```

<br>

## 📁 파일 구성

```text
ai/route_planner/domain/
├── README.md
├── schemas.py
└── trip_schemas.py
```

| 파일 | 책임 |
|---|---|
| `schemas.py` | 이동수단, 위치, Place 검색 결과, 이동시간 Matrix 모델 |
| `trip_schemas.py` | 일정 생성 요청·응답과 Route Option, Timeline DTO |

<br>

---

## 🚘 공통 경로 모델

공통 경로 및 Provider 모델은 `schemas.py`에 정의됩니다.

### TravelMode

지원하는 이동수단입니다.

```text
WALK
DRIVE
TRANSIT
```

`TravelMode`는 다음 영역에서 공통으로 사용됩니다.

- Travel Time Matrix 요청
- 이동수단별 Route Option
- Timeline
- Free Time Recommender 연동

### Location

Provider 요청에 사용하는 기본 좌표 모델입니다.

```text
Location
├── name
├── lat
└── lng
```

좌표 제약:

```text
-90 ≤ lat ≤ 90
-180 ≤ lng ≤ 180
```

`Location`에는 `place_id`가 없습니다.
따라서 실제 Matrix의 식별자 연결은 Provider 또는 Application 계층이 별도로 관리해야 합니다.

### PlaceResult

Google Maps 장소 검색 결과를 표현합니다.

```text
PlaceResult
├── place_id
├── name
├── formatted_address
├── location
├── rating
└── review_count
```

검증 규칙:

- `rating`: 0 이상 5 이하
- `review_count`: 0 이상
- 주소, 평점, 리뷰 수는 선택 필드

### TravelTimeElement

Provider가 반환한 한 이동 구간의 정보를 표현합니다.

```text
TravelTimeElement
├── origin_name
├── destination_name
├── origin_index
├── destination_index
├── duration_seconds
├── distance_meters
├── status
└── condition
```

`duration_seconds`가 존재하면 `duration_minutes` 속성으로 분 단위 값을 계산합니다.

```text
duration_minutes = round(duration_seconds / 60)
```

이 값은 내림이나 올림이 아니라 Python `round()` 결과를 사용합니다.

### TravelTimeMatrix

경로 최적화 Solver가 사용하는 이동시간 Matrix입니다.

```text
(origin_place_id, destination_place_id)
→ travel_minutes
```

타입:

```python
Dict[Tuple[str, str], int]
```

Matrix는 비대칭 구조를 허용합니다.

```text
A → B = 10분
B → A = 14분
```

### TravelTimeMatrixResult

정상 계산 구간과 누락 구간을 함께 반환합니다.

```text
TravelTimeMatrixResult
├── matrix
└── missing_elements
```

- `matrix`: 최적화에 사용할 수 있는 구간
- `missing_elements`: Provider가 계산하지 못했거나 시간이 없는 구간

### RouteData

Location 목록과 Matrix 결과를 함께 보존합니다.

```text
RouteData
├── locations
└── travel_time_matrix_result
```

편의 속성:

- `travel_time_matrix`
- `missing_travel_time_elements`

<br>

## 📥 일정 생성 요청 DTO

일정 생성 요청은 `TripPlanningRequestDTO`로 전달됩니다.

```text
TripPlanningRequestDTO
├── trip_id
├── timezone
├── days
└── pois
```

### PlaceDTO

START, END와 일반 장소에 사용하는 공통 장소 DTO입니다.

```text
PlaceDTO
├── place_id
├── name
├── lat
└── lng
```

현재 `PlaceDTO`의 좌표에는 `Location`과 같은 범위 Field 제약이 직접 선언되어 있지 않습니다.

### PoiCategory

지원하는 POI 카테고리입니다.

```text
TOURIST_ATTRACTION
RESTAURANT
CAFE
SHOPPING
ACTIVITY
HOTEL
ETC
```

### PoiDTO

사용자가 방문 대상으로 확정한 장소입니다.

```text
PoiDTO
├── poi_id
├── place_id
├── name
├── lat
├── lng
├── category
├── estimated_stay_minutes
├── priority
├── must_visit
└── preferred_day_index
```

필드 제약:

| 필드 | 제약 |
|---|---|
| `estimated_stay_minutes` | 1 이상 |
| `priority` | 1 이상 5 이하 |
| `preferred_day_index` | `None` 또는 1 이상 |
| `category` | 기본값 `ETC` |
| `priority` | 기본값 `3` |
| `must_visit` | 기본값 `True` |

`priority`와 `must_visit`은 요청 DTO에 포함되지만, 현재 정확 일자 배정의 최적화 목적에 실제로 어떻게 반영되는지는 Solver 문서를 기준으로 확인해야 합니다.

### DayConstraintDTO

하나의 여행 날짜 제약을 표현합니다.

```text
DayConstraintDTO
├── day_index
├── date
├── start_place
├── start_time
├── end_place
├── end_time
└── max_place_count
```

필드 제약:

| 필드 | 제약 |
|---|---|
| `day_index` | 1 이상 |
| `max_place_count` | `None` 또는 1 이상 |

`date`, `start_time`, `end_time`은 문자열입니다.
정확한 형식 검증은 Timeline Builder 또는 Application 처리 단계에서 수행됩니다.

### TripPlanningRequestDTO 검증

요청 생성 시 다음 규칙을 검증합니다.

#### 날짜 목록

```text
days가 비어 있음
→ ValueError
```

#### POI 목록

```text
pois가 비어 있음
→ ValueError
```

#### day_index 중복

```text
동일 day_index가 여러 번 등장
→ ValueError
```

#### preferred_day_index 참조

```text
POI의 preferred_day_index가 days에 존재하지 않음
→ ValueError
```

기본 timezone은 다음 값입니다.

```text
Asia/Tokyo
```

이 값이 실제로 유효한 IANA timezone인지는 Application 또는 Adapter 단계에서 별도로 검증합니다.

<br>

## 📅 일자 배정 결과 DTO

### DayPlanDTO

한 날짜의 POI 배정 결과입니다.

```text
DayPlanDTO
├── day_index
├── date
├── start_place
├── end_place
├── assigned_pois
├── estimated_total_stay_minutes
├── assignment_reason
└── route_options
```

`route_options`는 일자 배정 직후에는 빈 목록이며, 이후 이동수단별 경로 계산 과정에서 채워집니다.

```text
정확 일자 배정
→ DayPlanDTO(route_options=[])
→ 이동수단별 경로 계산
→ DayPlanDTO(route_options=[...])
```

`estimated_total_stay_minutes`는 배정된 POI의 `estimated_stay_minutes` 합계입니다.

### UnassignedPoiDTO

배정되지 않은 POI와 사유를 함께 보존합니다.

```text
UnassignedPoiDTO
├── poi
└── reason
```

미배정은 요청 실패와 다릅니다.
일부 POI만 배정할 수 있는 경우 전체 응답은 `PARTIAL_SUCCESS`가 될 수 있습니다.

<br>

## 🛣️ Route Option DTO

### RouteStopType

경로 내 정류장 타입입니다.

```text
START
POI
END
```

### RouteStopDTO

경로의 실제 방문 지점을 표현합니다.

```text
RouteStopDTO
├── stop_type
├── place_id
├── name
├── lat
└── lng
```

### RouteLegDTO

인접한 두 정류장 사이의 이동 구간입니다.

```text
RouteLegDTO
├── origin_place_id
├── destination_place_id
└── travel_minutes
```

현재 `travel_minutes`에는 명시적인 Pydantic 최소값 제약이 선언되어 있지 않습니다.
음수 이동시간 방지는 Provider 또는 Solver 계층 검증에 의존합니다.

### RouteOptionDTO

하나의 날짜와 이동수단에 대한 경로 옵션입니다.

```text
RouteOptionDTO
├── day_index
├── travel_mode
├── total_travel_minutes
├── ordered_stops
├── route_legs
├── missing_segments
├── warnings
└── timeline
```

필드 의미:

| 필드 | 의미 |
|---|---|
| `day_index` | Route Option이 속한 날짜 |
| `travel_mode` | DRIVE, WALK 또는 TRANSIT |
| `total_travel_minutes` | 전체 Route Leg 이동시간 합계 |
| `ordered_stops` | START부터 END까지 실제 방문 순서 |
| `route_legs` | 인접 정류장 사이 이동 구간 |
| `missing_segments` | Provider가 계산하지 못한 구간 설명 |
| `warnings` | 경로 생성 과정의 경고 |
| `timeline` | 선택적으로 생성된 실제 시간표 |

`timeline`은 기본값이 `None`입니다.

다음 경우 `None`이 유지될 수 있습니다.

- Timeline 생성 전
- Provider 누락으로 완전한 Route Option을 만들 수 없는 경우
- 후속 Timeline 생성이 의도적으로 생략된 경우

<br>

## ⏱️ Timeline DTO

### TimelineStopDTO

정류장별 도착·출발 정보를 표현합니다.

```text
TimelineStopDTO
├── stop_type
├── place_id
├── name
├── arrival_at
├── departure_at
└── stay_minutes
```

`stay_minutes`는 0 이상입니다.

일반적인 체류시간 정책:

```text
START → 0분
POI   → estimated_stay_minutes
END   → 0분
```

### TimelineDTO

하나의 Route Option 전체 시간표입니다.

```text
TimelineDTO
├── day_index
├── travel_mode
├── planned_start_at
├── planned_end_at
├── actual_end_at
├── total_travel_minutes
├── total_stay_minutes
├── timeline_stops
├── exceeds_planned_end
└── warnings
```

필드 제약:

| 필드 | 제약 |
|---|---|
| `day_index` | 1 이상 |
| `total_travel_minutes` | 0 이상 |
| `total_stay_minutes` | 0 이상 |
| `exceeds_planned_end` | 기본값 `False` |
| `warnings` | 기본 빈 목록 |

### Timeline 시각 형식

Timeline 시각 필드는 현재 `datetime` 객체가 아니라 문자열입니다.

```text
planned_start_at: str
planned_end_at: str
actual_end_at: str
arrival_at: str
departure_at: str
```

현재 Timeline Builder는 다음 형태의 문자열을 생성합니다.

```text
YYYY-MM-DDTHH:MM
```

현재 생성 단계에서는 timezone offset을 문자열에 포함하지 않습니다.

예:

```text
2026-07-23T09:30
```

따라서 Free Time Recommender가 Timeline을 사용할 때 여행 timezone을 별도로 적용하거나 변환해야 합니다.

<br>

## 📤 최종 응답 DTO

### TripPlanningStatus

일정 생성 상태입니다.

```text
SUCCESS
PARTIAL_SUCCESS
FAILED
```

현재 일자 배정 Adapter는 다음 상태를 사용합니다.

```text
미배정 POI 없음
→ SUCCESS

미배정 POI 있음
→ PARTIAL_SUCCESS
```

`FAILED`는 Enum에 정의되어 있지만 현재 정상 일자 배정 응답 조립 흐름에서는 직접 선택되지 않습니다.
실행 실패는 주로 예외로 전달됩니다.

### TripPlanningResponseDTO

최종 일정 최적화 응답입니다.

```text
TripPlanningResponseDTO
├── trip_id
├── status
├── day_plans
├── unassigned_pois
└── warnings
```

`day_plans`에는 일자 배정 결과와 이동수단별 Route Option이 함께 포함됩니다.

```text
TripPlanningResponseDTO
└── day_plans
    └── route_options
        └── timeline
```

<br>

## ✅ 검증 규칙

Pydantic DTO 검증 외에도 Solver와 Builder가 추가 불변조건을 검증합니다.

### POI 식별자

```text
poi_id 중복
→ 일자 배정 Adapter에서 ValueError
```

### place_id

START, END와 배정 POI의 `place_id`는 같은 Route Option에서 모두 고유해야 합니다.

```text
중복 place_id
→ Route Option 생성 거부
```

### 정확 경로 결과

Route Option 변환 단계에서 다음을 다시 검증합니다.

- 첫 장소는 START
- 마지막 장소는 END
- 중간 POI 중복 없음
- 입력 POI 누락 없음
- 알 수 없는 POI 없음
- 정확 Solver 결과의 전체 장소 집합이 입력과 동일
- 모든 인접 구간이 Matrix에 존재
- Route Leg 개수가 장소 수보다 정확히 하나 적음
- Route Leg 이동시간 합계와 정확 Solver 총비용 일치

### Timeline 결과

Timeline 생성 단계에서 다음을 검증합니다.

- DayConstraint, DayPlan, Route Option의 `day_index` 일치
- DayConstraint와 DayPlan의 `date` 일치
- `missing_segments`가 없어야 함
- 최소 START와 END 정류장 존재
- 첫 정류장은 START
- 마지막 정류장은 END
- START와 END의 `place_id`가 날짜 제약과 일치
- Route Leg 개수와 정류장 개수 관계 일치
- Route Leg 순서와 ordered stops 순서 일치
- Route Leg 이동시간 합계와 총 이동시간 일치

<br>

## 🔒 도메인 불변조건

Route Planner의 주요 불변조건은 다음과 같습니다.

### 요청 수준

```text
days는 비어 있을 수 없음
pois는 비어 있을 수 없음
day_index는 고유해야 함
preferred_day_index는 실제 날짜를 참조해야 함
```

### 일자 배정 수준

```text
하나의 POI는 최대 한 날짜에만 배정
동일 POI가 배정과 미배정에 동시에 포함될 수 없음
Solver 결과와 DayPlan의 POI 집합은 동일해야 함
```

### 경로 수준

```text
경로 시작은 START
경로 종료는 END
모든 배정 POI를 정확히 한 번 방문
알 수 없는 장소 포함 금지
모든 Route Leg는 Matrix에 존재
Route Leg 합계 = total_travel_minutes
```

### Timeline 수준

```text
Timeline의 날짜와 Route Option 날짜 일치
정류장 순서와 Route Leg 순서 일치
START와 END 체류시간은 0
POI 체류시간은 배정된 POI 정보에서 조회
actual_end_at > planned_end_at이면 초과 경고 생성
```

<br>

## ⚠️ 현재 모델의 주의사항

### 날짜와 시각이 문자열임

`date`, `start_time`, `end_time`과 Timeline 시각은 문자열입니다.

따라서 형식 검증과 timezone 적용이 한 곳에서 완전히 보장되지 않고, Application, Builder와 Adapter에 분산되어 있습니다.

### Timeline이 timezone-naive임

Route Planner Timeline 문자열에는 현재 timezone offset이 포함되지 않습니다.

```text
2026-07-23T09:30
```

Free Time Recommender는 여행 timezone을 받아 이 문자열을 timezone-aware datetime으로 변환해야 합니다.

### PlaceDTO 좌표 범위

`Location`에는 위도·경도 범위 검증이 있지만 `PlaceDTO`와 `PoiDTO`에는 같은 Field 제약이 직접 선언되어 있지 않습니다.

### FAILED 상태

`FAILED` 상태는 정의되어 있지만 현재 일반적인 Solver 실패는 응답 상태가 아니라 예외로 전달됩니다.

### priority와 must_visit

`PoiDTO`에 존재하지만 정확 일자 배정 목적함수에 어떻게 사용되는지는 Solver 구현을 기준으로 확인해야 합니다.
DTO에 필드가 존재한다는 이유만으로 최적화에 반영된다고 가정하면 안 됩니다.

### RouteLegDTO 이동시간

`RouteLegDTO.travel_minutes`에는 DTO 수준의 최소값 제약이 없습니다.
음수 값 방지는 Provider와 Solver의 데이터 신뢰성에 의존합니다.

<br>

## 🔗 관련 문서

| 문서 | 설명 |
|---|---|
| [Route Planner](../README.md) | 전체 일정 최적화 구조 |
| [Application](../application/README.md) | 요청 DTO를 이용한 전체 실행 흐름 |
| [Solvers](../solvers/README.md) | 도메인 모델의 불변조건을 검증하는 정확 Solver |
| [Providers](../providers/README.md) | `TravelTimeMatrixResult` 생성과 누락 구간 처리 |
| [Evaluation](../evaluation/README.md) | 응답과 정확 경로 결과의 평가 기준 |
| [Free Time Recommender Domain](../../free_time_recommender/domain/README.md) | Route Option과 Timeline을 이용하는 추천 도메인 |
| [Free Time Recommender Adapters](../../free_time_recommender/adapters/README.md) | Route Planner DTO 변환과 timezone 보정 |
