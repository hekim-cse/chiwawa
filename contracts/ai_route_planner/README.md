# AI Route Planner 응답 계약

이 디렉터리는 Backend가 Modal 통합 응답 DTO를 구현할 때 사용하는
버전 관리 계약을 보관한다.

## 계약 원본

계약의 원본은 다음 Pydantic DTO이다.

```text
ai.free_time_recommender.adapters.modal_response
└── TripPlanningWithRecommendationsResponseDTO
```

`trip_planning_with_recommendations_response.schema.json`은 원본 DTO에서
생성된 JSON Schema이며 직접 수정하지 않는다.

## Schema 생성

저장소 루트에서 다음 명령을 실행한다.

```bash
python -m ai.route_planner.scripts.export_modal_response_schema
```

DTO 변경 후 Schema를 다시 생성하지 않으면 계약 테스트가 실패한다.

## 대표 Fixture

Backend 계약 테스트에는 다음 Fixture를 함께 사용한다.

```text
ai/route_planner/tests/fixtures/
└── trip_planning_with_recommendations_response.json
```

Fixture는 다음 계약을 포함한다.

- `PARTIAL_SUCCESS` 전체 상태
- Timeline이 있는 `SUCCESS` 추천
- Timeline이 없는 `UNAVAILABLE` 추천
- 미배정 POI와 경고
- 경로 geometry, 추천 후보 및 일정 삽입 영향
