# 🧱 Free Time Recommender Domain

Free Time Recommender가 사용하는 **추천 정책**, **시간 예산**, **경로 Geometry**, **장소 후보와 카테고리 모델**을 정의합니다.

이 디렉터리는 Google API를 직접 호출하거나 추천 파이프라인을 조정하지 않습니다.
외부 SDK와 Application 구현에 의존하지 않는 순수 도메인 객체와 검증 규칙을 제공합니다.

> 상위 문서: [Free Time Recommender](../README.md)

<br>

## 📚 목차

1. [🎯 디렉터리 역할](#-디렉터리-역할)
2. [📁 파일 구성](#-파일-구성)
3. [🗂️ 추천 카테고리](#-추천-카테고리)
4. [📍 장소 후보 모델](#-장소-후보-모델)
5. [🗺️ 경로 Geometry 모델](#-경로-geometry-모델)
6. [⚙️ RecommendationPolicy](#-recommendationpolicy)
7. [⏱️ RecommendationTimeWindow](#-recommendationtimewindow)
8. [🚶 후보 경유 이동시간](#-후보-경유-이동시간)
9. [✅ 추천 가능성 평가](#-추천-가능성-평가)
10. [🚫 추천 거절 사유](#-추천-거절-사유)
11. [🔒 도메인 불변조건](#-도메인-불변조건)
12. [🧪 테스트 관점](#-테스트-관점)
13. [⚠️ 현재 모델의 주의사항](#-현재-모델의-주의사항)
14. [🔗 관련 문서](#-관련-문서)

<br>

---

## 🎯 디렉터리 역할

`ai/free_time_recommender/domain`은 다음 책임을 가집니다.

- 추천 카테고리 Enum과 표시명 정의
- 서버 관리 추천 카테고리 순서 정의
- Search Along Route Query 정의
- 외부 검색 결과를 내부 Place Candidate로 표현
- 후보와 원본 Route Leg의 연결 정보 보존
- 지도 SDK에 독립적인 좌표 모델 정의
- 경로 Geometry 조회 Query 정의
- encoded polyline 모델 정의
- 추천 시간 정책 정의
- 추천 삽입 시간 범위 정의
- 후보 경유 이동시간 정의
- 추천 가능 여부와 거절 사유 계산
- 모든 도메인 객체의 기본 타입과 범위 검증

도메인 모델은 다음 계층 사이의 공통 계약입니다.

```text
Route Planner Adapter
→ Domain Model
→ Application Use Case
→ Provider Port
→ Domain Result
```

<br>

## 📁 파일 구성

```text
ai/free_time_recommender/domain/
├── README.md
├── place_candidate.py
├── recommendation_budget.py
├── recommendation_policy.py
└── route_geometry.py
```

| 파일 | 책임 |
|---|---|
| `place_candidate.py` | 추천 카테고리, 검색 Query와 장소 후보 |
| `route_geometry.py` | 좌표, 이동수단, Geometry Query와 polyline |
| `recommendation_policy.py` | 추천 기준값 |
| `recommendation_budget.py` | 시간 범위, 이동시간과 추천 가능성 평가 |

<br>

---

## 🗂️ 추천 카테고리

### RecommendationCategory

사용자에게 노출할 추천 카테고리입니다.

```text
LANDMARK
CAFE
CULTURE
PARK
RESTAURANT
```

카테고리는 클라이언트가 임의 문자열로 전달하는 값이 아니라 서버 도메인 Enum으로 관리됩니다.

### RecommendationCategoryDefinition

카테고리와 화면 표시명을 연결합니다.

```text
RecommendationCategoryDefinition
├── category
└── display_name
```

검증 규칙:

- `category`는 `RecommendationCategory`
- `display_name`은 비어 있지 않은 문자열

### RecommendationCategoryCatalog

추천 카테고리 목록과 순서를 보존합니다.

```text
RecommendationCategoryCatalog
└── definitions
```

`definitions`는 반드시 tuple이어야 하며 비어 있을 수 없습니다.

다음 중복을 허용하지 않습니다.

```text
중복 category
중복 display_name
```

카탈로그 순서는 다음 두 의미를 가집니다.

```text
1. 카테고리 검색 순서
2. 중복 Place Candidate의 대표 카테고리 결정 순서
```

### 기본 카탈로그

기본 카테고리 순서는 다음과 같습니다.

```text
1. LANDMARK   → 랜드마크·관광명소
2. CAFE       → 카페
3. CULTURE    → 문화·전시 공간
4. PARK       → 공원·정원
5. RESTAURANT → 음식점
```

상수:

```text
DEFAULT_RECOMMENDATION_CATEGORY_CATALOG
```

<br>

## 📍 장소 후보 모델

### AlongRoutePlaceSearchQuery

하나의 카테고리를 대상으로 경로 주변 장소를 검색할 조건입니다.

```text
AlongRoutePlaceSearchQuery
├── encoded_polyline
├── category
├── page_size
├── language_code
└── region_code
```

검증 규칙:

| 필드 | 제약 |
|---|---|
| `encoded_polyline` | 비어 있지 않은 문자열 |
| `category` | `RecommendationCategory` |
| `page_size` | 1 이상 20 이하 정수 |
| `language_code` | 비어 있지 않은 문자열 |
| `region_code` | 비어 있지 않은 문자열 |

`page_size`는 bool을 정수로 허용하지 않습니다.

```text
True
False
→ TypeError
```

### PlaceCandidate

외부 Places Provider 응답을 내부 추천 후보로 변환한 모델입니다.

```text
PlaceCandidate
├── place_id
├── name
├── coordinate
├── category
├── formatted_address
├── rating
└── user_rating_count
```

필수 필드:

- `place_id`
- `name`
- `coordinate`
- `category`

선택 필드:

- `formatted_address`
- `rating`
- `user_rating_count`

### rating

```text
0 ≤ rating ≤ 5
```

다음 값은 허용하지 않습니다.

- bool
- NaN
- Infinity
- 음수
- 5 초과

### user_rating_count

```text
user_rating_count ≥ 0
```

bool은 정수로 허용하지 않습니다.

### CategoryPlaceCandidates

한 카테고리의 중복 제거된 장소 후보 그룹입니다.

```text
CategoryPlaceCandidates
├── category
├── display_name
└── candidates
```

현재 이 모델에는 별도의 `__post_init__` 검증이 선언되어 있지 않습니다.

따라서 타입과 카테고리 일치에 대한 강한 검증은 `CategoryRouteLegPlaceCandidates`와 비교해 상대적으로 약합니다.

### RouteLegPlaceCandidate

장소 후보와 해당 후보를 발견한 원본 Route Leg를 연결합니다.

```text
RouteLegPlaceCandidate
├── candidate
├── day_index
├── leg_index
├── origin_place_id
└── destination_place_id
```

이 모델이 보존하는 의미:

```text
이 후보는
특정 날짜의
특정 Route Leg에서
검색되었다
```

검증 규칙:

| 필드 | 제약 |
|---|---|
| `candidate` | `PlaceCandidate` |
| `day_index` | 1 이상 정수 |
| `leg_index` | 0 이상 정수 |
| `origin_place_id` | 비어 있지 않은 문자열 |
| `destination_place_id` | 비어 있지 않은 문자열 |

출발지와 도착지는 같을 수 없습니다.

```text
origin_place_id == destination_place_id
→ ValueError
```

### CategoryRouteLegPlaceCandidates

Route Leg 식별 정보까지 포함된 카테고리별 후보 묶음입니다.

```text
CategoryRouteLegPlaceCandidates
├── category
├── display_name
└── candidates
```

검증 규칙:

- `category`는 `RecommendationCategory`
- `display_name`은 비어 있지 않은 문자열
- `candidates`는 tuple
- 모든 원소는 `RouteLegPlaceCandidate`
- 각 후보의 카테고리가 그룹 카테고리와 동일

```text
candidate.candidate.category
= group.category
```

후보를 잘못된 카테고리 그룹에 넣으면 ValueError가 발생합니다.

<br>

## 🗺️ 경로 Geometry 모델

### RouteTravelMode

Geometry 조회용 이동수단입니다.

```text
WALK
DRIVE
TRANSIT
```

Route Planner의 `TravelMode`와 값은 같지만 별도의 Enum입니다.

```text
Route Planner TravelMode
≠
Free Time Recommender RouteTravelMode
```

두 Enum 사이의 변환은 Adapter 또는 Application 계층 책임입니다.

### GeoCoordinate

외부 지도 SDK에 의존하지 않는 좌표 모델입니다.

```text
GeoCoordinate
├── latitude
└── longitude
```

검증 범위:

```text
-90 ≤ latitude ≤ 90
-180 ≤ longitude ≤ 180
```

다음 값은 허용하지 않습니다.

- bool
- 문자열
- NaN
- Infinity
- 범위를 벗어난 좌표

### RouteGeometryQuery

두 장소 사이의 Geometry 조회 조건입니다.

```text
RouteGeometryQuery
├── origin
├── destination
├── travel_mode
└── departure_at
```

검증 규칙:

- `origin`은 `GeoCoordinate`
- `destination`은 `GeoCoordinate`
- `travel_mode`는 `RouteTravelMode`
- `departure_at`이 있으면 datetime
- `departure_at`이 있으면 timezone-aware

### TRANSIT Geometry

TRANSIT에는 출발시각이 필수입니다.

```text
travel_mode = TRANSIT
AND
departure_at = None
→ ValueError
```

또한 timezone-naive datetime도 허용하지 않습니다.

```text
TRANSIT
→ timezone-aware departure_at 필수
```

WALK와 DRIVE는 `departure_at=None`을 허용합니다.

### RouteLegGeometry

Provider가 반환한 encoded polyline입니다.

```text
RouteLegGeometry
└── encoded_polyline
```

encoded polyline은 비어 있지 않은 문자열이어야 합니다.

### OptimizedRouteLegGeometryQuery

최적화 경로의 특정 구간과 Geometry Query를 결합합니다.

```text
OptimizedRouteLegGeometryQuery
├── day_index
├── leg_index
├── origin_place_id
├── destination_place_id
└── geometry_query
```

### OptimizedRouteLegGeometry

최적화 경로 구간 식별 정보와 실제 Geometry를 결합합니다.

```text
OptimizedRouteLegGeometry
├── day_index
├── leg_index
├── origin_place_id
├── destination_place_id
└── geometry
```

두 모델은 공통 검증 함수를 사용합니다.

```text
_validate_optimized_route_leg()
```

공통 검증:

- `day_index`는 1 이상 정수
- `leg_index`는 0 이상 정수
- 출발·도착 `place_id`는 비어 있지 않음
- 출발지와 도착지가 다름

<br>

## ⚙️ RecommendationPolicy

추천 정책은 불변 dataclass입니다.

```text
RecommendationPolicy
├── minimum_stay_minutes
├── maximum_one_way_travel_minutes
├── maximum_one_way_distance_meters
└── candidate_limit
```

### minimum_stay_minutes

추천 장소에서 확보해야 할 최소 체류시간입니다.

```text
1 이상 정수
```

### maximum_one_way_travel_minutes

한쪽 방향에서 허용하는 최대 이동시간입니다.

```text
0 이상 정수
```

다음 두 구간에 각각 적용됩니다.

```text
이전 장소 → 후보
후보 → 다음 장소
```

### maximum_one_way_distance_meters

한쪽 방향에서 허용하는 최대 이동거리입니다.

```text
0 이상 정수
```

주의할 점은 이 값이 Policy에 존재하지만 `EvaluateRecommendationFeasibility`의 시간 계산에는 직접 사용되지 않는다는 점입니다.

거리 제한 적용은 후보 경로 지표를 조립하는 Application 또는 별도 필터링 단계에서 확인해야 합니다.

### candidate_limit

추천 결과에 유지할 후보 수 제한입니다.

```text
1 이상 정수
```

현재 `AlongRoutePlaceSearchQuery.page_size`와는 별개의 값입니다.

```text
page_size
→ Places 검색 요청 결과 수

candidate_limit
→ 추천 정책의 후보 제한
```

두 값이 같다고 가정하면 안 됩니다.

### bool 검증

Python에서 bool은 int의 하위 타입이지만 정책 값으로 허용하지 않습니다.

```text
True
False
→ TypeError
```

<br>

## ⏱️ RecommendationTimeWindow

추천 장소 삽입에 사용할 시간 범위입니다.

```text
RecommendationTimeWindow
├── day_index
├── start_at
├── end_at
├── available_minutes
├── previous_place_id
└── next_place_id
```

현재 코드의 설명은 이 모델을 다음처럼 정의합니다.

```text
마지막 방문지와 최종 도착지 사이에
추천 장소를 삽입할 시간 범위
```

`RecommendationTimeWindow` 자체는 마지막 구간 전용 모델입니다.

모든 Route Leg의 삽입 평가는 Adapter가 별도로 생성하는 `RouteLegInsertionWindow`를 사용합니다.

### day_index

```text
1 이상 정수
```

### start_at과 end_at

둘 다 datetime이어야 합니다.

시간 정밀도는 분 단위만 허용합니다.

```text
second = 0
microsecond = 0
```

초 또는 마이크로초가 포함되면 ValueError가 발생합니다.

### timezone 형식

두 datetime은 같은 timezone 형식을 사용해야 합니다.

허용:

```text
둘 다 timezone-naive
둘 다 timezone-aware
```

거부:

```text
start_at은 aware
end_at은 naive
```

현재 도메인 모델 자체는 두 값이 모두 timezone-aware일 것을 강제하지 않습니다.

timezone 적용 책임은 Adapter 계층에 있습니다.

### 시간 순서

```text
end_at > start_at
```

같거나 더 이르면 ValueError가 발생합니다.

### available_minutes

```text
0 이상 정수
```

실제 시간 차와 정확히 일치해야 합니다.

```text
available_minutes
=
floor((end_at - start_at) / 60초)
```

분 단위 datetime만 허용하므로 정상 입력에서는 실제 분 차와 일치합니다.

### 장소 식별자

`previous_place_id`와 `next_place_id`는 비어 있지 않은 문자열이어야 합니다.

현재 두 `place_id`가 서로 달라야 한다는 검증은 `RecommendationTimeWindow` 자체에는 선언되어 있지 않습니다.

<br>

## 🚶 후보 경유 이동시간

### CandidateTravelTimes

후보를 경유할 때 필요한 양쪽 편도 이동시간입니다.

```text
CandidateTravelTimes
├── previous_to_candidate_minutes
└── candidate_to_next_minutes
```

두 값은 모두 0 이상 정수입니다.

```text
이전 장소 → 후보
후보 → 다음 장소
```

현재 모델에는 원래 Route Leg 이동시간이 포함되지 않습니다.

따라서 현재 추천 가능성 계산은 “원래 경로 대비 추가 이동시간”이 아니라, 시간 범위 안에 후보 경유 이동과 체류를 모두 수용할 수 있는지를 계산합니다.

<br>

## ✅ 추천 가능성 평가

### EvaluateRecommendationFeasibility

순수 도메인 서비스입니다.

입력:

```text
RecommendationTimeWindow
RecommendationPolicy
CandidateTravelTimes
```

출력:

```text
RecommendationFeasibility
├── required_minutes
├── remaining_minutes
└── rejection_reasons
```

### required_minutes

필요한 총시간은 다음과 같습니다.

```text
이전 장소 → 후보 이동시간
+ 최소 체류시간
+ 후보 → 다음 장소 이동시간
```

수식:

```text
required_minutes
=
previous_to_candidate_minutes
+ minimum_stay_minutes
+ candidate_to_next_minutes
```

### remaining_minutes

```text
remaining_minutes
=
window.available_minutes
- required_minutes
```

음수 값도 결과로 허용됩니다.

```text
remaining_minutes < 0
→ 시간 부족 거절 사유 추가
```

### 추천 가능 여부

`RecommendationFeasibility.is_recommendable`은 거절 사유가 없는지를 확인합니다.

```text
rejection_reasons가 비어 있음
→ True

하나 이상 존재
→ False
```

### 편도 이동시간 제한

양쪽 방향을 각각 독립적으로 검증합니다.

```text
previous_to_candidate_minutes
> maximum_one_way_travel_minutes
→ 거절
```

```text
candidate_to_next_minutes
> maximum_one_way_travel_minutes
→ 거절
```

제한값과 같은 경우는 허용됩니다.

```text
travel_minutes == maximum
→ 통과
```

### 총시간 제한

```text
remaining_minutes < 0
→ 거절
```

정확히 0이면 추천 가능합니다.

```text
remaining_minutes = 0
→ 통과
```

### 거리 제한

`maximum_one_way_distance_meters`는 `RecommendationPolicy`에 존재하지만 이 평가 클래스의 입력에는 거리값이 없습니다.

따라서 `EvaluateRecommendationFeasibility`는 거리 제한을 검사하지 않습니다.

```text
현재 순수 평가
→ 이동시간과 최소 체류시간만 검증

거리 검증
→ 다른 계층 또는 별도 로직 책임
```

<br>

## 🚫 추천 거절 사유

### RecommendationRejectionReason

지원하는 거절 사유는 세 가지입니다.

```text
PREVIOUS_TO_CANDIDATE_LIMIT_EXCEEDED
CANDIDATE_TO_NEXT_LIMIT_EXCEEDED
INSUFFICIENT_TOTAL_TIME
```

### 복수 거절 사유

한 후보는 여러 사유로 동시에 거절될 수 있습니다.

예:

```text
이전 장소 → 후보 이동시간 초과
후보 → 다음 장소 이동시간 초과
총시간도 부족
```

결과:

```text
rejection_reasons = (
    PREVIOUS_TO_CANDIDATE_LIMIT_EXCEEDED,
    CANDIDATE_TO_NEXT_LIMIT_EXCEEDED,
    INSUFFICIENT_TOTAL_TIME,
)
```

현재 사유 추가 순서는 코드에 고정되어 있습니다.

```text
1. 이전 장소 → 후보 제한
2. 후보 → 다음 장소 제한
3. 총시간 부족
```

호출 측이 순서를 사용자 메시지 우선순위로 해석하면 안 됩니다.

<br>

## 🔒 도메인 불변조건

### 카테고리

```text
카탈로그는 비어 있을 수 없음
카테고리 중복 금지
표시명 중복 금지
카테고리 그룹과 후보 카테고리 일치
```

### 장소 후보

```text
place_id와 name은 비어 있을 수 없음
좌표는 유효 범위
rating은 0~5의 유한한 수
user_rating_count는 0 이상
```

### Route Leg 연결

```text
day_index ≥ 1
leg_index ≥ 0
출발·도착 place_id는 비어 있지 않음
출발지와 도착지는 다름
```

### Geometry

```text
encoded_polyline은 비어 있을 수 없음
TRANSIT에는 timezone-aware departure_at 필요
```

### 추천 정책

```text
minimum_stay_minutes ≥ 1
maximum_one_way_travel_minutes ≥ 0
maximum_one_way_distance_meters ≥ 0
candidate_limit ≥ 1
```

### 시간 범위

```text
end_at > start_at
초와 마이크로초는 0
start_at과 end_at의 timezone 형식 일치
available_minutes는 실제 시간 차와 일치
```

### 추천 가능성

```text
required_minutes
= 양쪽 이동시간 + 최소 체류시간

remaining_minutes
= available_minutes - required_minutes

거절 사유 없음
→ recommendable
```

<br>

## 🧪 테스트 관점

### RecommendationCategoryCatalog

- 빈 definitions
- list 전달
- 중복 category
- 중복 display_name
- 기본 카탈로그 순서
- 잘못된 Definition 타입

### AlongRoutePlaceSearchQuery

- 정상 page_size 1
- 정상 page_size 20
- page_size 0
- page_size 21
- bool page_size
- 빈 polyline
- 빈 language_code
- 빈 region_code

### PlaceCandidate

- 정상 후보
- 빈 place_id
- 빈 name
- 잘못된 coordinate 타입
- rating 0
- rating 5
- rating 음수
- rating 5 초과
- NaN과 Infinity
- 음수 user_rating_count
- bool user_rating_count

### RouteLegPlaceCandidate

- day_index 경계값
- leg_index 경계값
- 빈 장소 식별자
- 동일 출발·도착 장소
- 잘못된 Candidate 타입

### CategoryRouteLegPlaceCandidates

- tuple 아닌 candidates
- 잘못된 Candidate 원소
- 그룹 카테고리 불일치
- 빈 후보 tuple
- 표시명 검증

### GeoCoordinate

- 위도 -90과 90
- 경도 -180과 180
- 범위 초과
- bool
- NaN
- Infinity

### RouteGeometryQuery

- WALK에서 departure_at 없음
- DRIVE에서 departure_at 없음
- TRANSIT의 timezone-aware departure_at
- TRANSIT의 departure_at 없음
- timezone-naive datetime
- 잘못된 이동수단 타입

### RouteLegGeometry

- 정상 encoded polyline
- 빈 문자열
- 공백 문자열
- 문자열 아닌 값

### RecommendationPolicy

- 최소 체류시간 1
- 최대 이동시간 0
- 최대 거리 0
- 후보 제한 1
- 음수 값
- bool 값
- float 값

### RecommendationTimeWindow

- 정상 naive 시간
- 정상 aware 시간
- timezone 형식 불일치
- 같은 시작·종료 시각
- 역전된 시간
- 초 단위 포함
- microsecond 포함
- available_minutes 불일치
- 빈 place_id

### EvaluateRecommendationFeasibility

- 정확히 시간에 맞는 후보
- 1분 부족
- 이전 방향 제한 초과
- 다음 방향 제한 초과
- 양쪽 방향 모두 초과
- 총시간만 부족
- 복수 거절 사유 순서
- `is_recommendable`

<br>

## ⚠️ 현재 모델의 주의사항

### TimeWindow의 범위가 일반적이지 않음

현재 `RecommendationTimeWindow`는 마지막 방문지와 최종 도착지 사이의 단일 시간 범위를 표현합니다.

모든 Route Leg에 대한 추천 삽입 평가는 `RoutePlannerTimelineAdapter.to_route_leg_insertion_windows()`가 생성하는 `RouteLegInsertionWindow`를 사용합니다.

### 거리 제한은 순수 Feasibility에서 사용되지 않음

Policy에는 최대 편도 거리가 존재하지만 `EvaluateRecommendationFeasibility`는 거리 입력을 받지 않습니다.

거리 제한을 이미 검증한다고 문서화하면 부정확합니다.

### 원래 Route Leg 비용이 없음

`CandidateTravelTimes`에는 후보 경유 양쪽 이동시간만 있습니다.

원래 Route Leg 비용과의 차이인 추가 이동시간은 이 도메인 서비스에서 계산하지 않습니다.

### RouteTravelMode가 별도 Enum임

Route Planner `TravelMode`와 값이 같아도 동일 타입이 아닙니다.

명시적 변환이 필요합니다.

### TimeWindow는 timezone-aware를 강제하지 않음

두 datetime의 timezone 형식 일치만 검증합니다.

실제 여행 timezone 적용은 Adapter 계층 책임입니다.

### CategoryPlaceCandidates 검증이 약함

`CategoryPlaceCandidates`에는 현재 별도의 `__post_init__` 검증이 없습니다.

반면 `CategoryRouteLegPlaceCandidates`는 그룹과 후보 카테고리 일치를 검증합니다.

### 검색 수와 추천 수 제한이 다름

```text
AlongRoutePlaceSearchQuery.page_size
RecommendationPolicy.candidate_limit
```

두 필드는 서로 다른 책임을 가집니다.

### 모델은 불변 객체임

주요 도메인 모델은 `@dataclass(frozen=True)`로 선언되어 있습니다.

생성 이후 필드를 직접 수정하지 않고 새로운 객체를 생성해야 합니다.

<br>

## 🔗 관련 문서

| 문서 | 설명 |
|---|---|
| [Free Time Recommender](../README.md) | 추천 모듈 전체 구조 |
| [Application](../application/README.md) | 도메인 모델을 조합하는 추천 Use Case |
| [Adapters](../adapters/README.md) | Route Planner DTO를 도메인 모델로 변환 |
| [Providers](../providers/README.md) | Geometry, Places와 후보 경로 지표 조회 |
| [Route Planner Domain](../../route_planner/domain/README.md) | 추천 입력이 되는 Route Option과 Timeline DTO |
| [Route Planner Solvers](../../route_planner/solvers/README.md) | 최적화 경로와 Timeline 생성 |
