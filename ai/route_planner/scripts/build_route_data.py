# 터미널에서 장소명을 입력받아 RouteData 생성 결과를 확인하는 실행 스크립트
import argparse

from ai.route_planner.domain.schemas import TravelMode
from ai.route_planner.providers.route_data_provider import RouteDataProvider


# 쉼표로 구분된 장소명 문자열을 장소명 리스트로 변환하는 함수
def parse_place_names(raw_places: str) -> list[str]:
    place_names = [
        place_name.strip()
        for place_name in raw_places.split(",")
        if place_name.strip()
    ]

    if len(place_names) < 2:
        raise ValueError("At least two place names are required.")

    return place_names


# 문자열로 입력받은 이동 방식을 TravelMode enum으로 변환하는 함수
def parse_travel_mode(raw_travel_mode: str) -> TravelMode:
    try:
        return TravelMode(raw_travel_mode.upper())
    except ValueError as exc:
        valid_modes = ", ".join(mode.value for mode in TravelMode)
        raise ValueError(f"Invalid travel mode. Choose one of: {valid_modes}") from exc


# RouteData 생성 결과를 콘솔에 출력하는 함수
def print_route_data_result(route_data) -> None:
    print("\n[장소 좌표]")
    print("=" * 60)
    for location in route_data.locations:
        print(f"{location.name}: {location.lat}, {location.lng}")

    print("\n[이동 시간 행렬]")
    print("=" * 60)
    for (origin, destination), minutes in sorted(route_data.travel_time_matrix.items()):
        if origin == destination:
            continue

        print(f"{origin} -> {destination}: {minutes}분")

    print("\n[이동 시간 누락 구간]")
    print("=" * 60)

    missing_elements = route_data.missing_travel_time_elements
    if not missing_elements:
        print("누락 구간 없음")
        return

    for element in missing_elements:
        if element.origin_name == element.destination_name:
            continue

        print(
            f"{element.origin_name} -> {element.destination_name}: "
            f"duration 없음 / status={element.status} / condition={element.condition}"
        )


# 스크립트 실행 진입점
def main() -> None:
    parser = argparse.ArgumentParser(
        description="장소명 목록을 기반으로 Google Places/Routes API 경로 데이터를 생성합니다."
    )

    parser.add_argument(
        "--places",
        required=True,
        help="쉼표로 구분된 장소명 목록입니다. 예: '오사카 난바역,오사카 도톤보리'",
    )

    parser.add_argument(
        "--travel-mode",
        default=TravelMode.TRANSIT.value,
        choices=[mode.value for mode in TravelMode],
        help="이동 방식입니다. WALK, DRIVE, TRANSIT 중 하나를 선택합니다.",
    )

    args = parser.parse_args()

    place_names = parse_place_names(args.places)
    travel_mode = parse_travel_mode(args.travel_mode)

    provider = RouteDataProvider()
    route_data = provider.build_route_data(
        place_names=place_names,
        travel_mode=travel_mode,
    )

    print_route_data_result(route_data)


if __name__ == "__main__":
    main()
