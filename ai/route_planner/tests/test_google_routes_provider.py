# GoogleRoutesProvider 단위 테스트
from ai.route_planner.domain.schemas import Location, TravelTimeElement, TravelMode
from ai.route_planner.providers.google_routes_provider import GoogleRoutesProvider


# 자기 자신으로 이동하는 self-pair 구간은 missing_elements에 포함하지 않는지 검증
def test_build_travel_time_matrix_result_skips_self_pair_elements():
    provider = GoogleRoutesProvider(api_key="test-api-key")

    elements = [
        TravelTimeElement(
            origin_name="a",
            destination_name="a",
            origin_index=0,
            destination_index=0,
            duration_seconds=None,
            condition="ROUTE_NOT_FOUND",
        ),
        TravelTimeElement(
            origin_name="a",
            destination_name="b",
            origin_index=0,
            destination_index=1,
            duration_seconds=600,
            condition="ROUTE_EXISTS",
        ),
        TravelTimeElement(
            origin_name="b",
            destination_name="a",
            origin_index=1,
            destination_index=0,
            duration_seconds=None,
            condition="ROUTE_NOT_FOUND",
        ),
    ]

    provider.compute_route_matrix = lambda locations, travel_mode: elements

    result = provider.build_travel_time_matrix_result(
        locations=[
            Location(name="a", lat=0, lng=0),
            Location(name="b", lat=1, lng=1),
        ],
        travel_mode=TravelMode.DRIVE,
    )

    assert result.matrix == {
        ("a", "b"): 10,
    }
    assert len(result.missing_elements) == 1
    assert result.missing_elements[0].origin_name == "b"
    assert result.missing_elements[0].destination_name == "a"
