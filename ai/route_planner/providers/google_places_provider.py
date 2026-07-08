# Google Places API를 호출해서 “검색어”를 “좌표/주소/평점 정보”로 변환하는 Provider
from typing import List, Optional

import httpx

from ai.route_planner.domain.schemas import Location, PlaceResult
from ai.route_planner.providers.env import get_google_maps_api_key


# Google Places API를 호출해서 장소 검색어 -> 좌표/주소/평점 정보로 변환하는 Provider
class GooglePlacesProvider:
    BASE_URL = "https://places.googleapis.com/v1/places:searchText"

    # GooglePlacesProvider 생성자
    # api_key: Google Places API 키 (없으면 환경변수에서 가져옴)
    # timeout_seconds: API 호출 타임아웃 (초)
    def __init__(self, api_key: Optional[str] = None, timeout_seconds: float = 10.0):
        self.api_key = api_key or get_google_maps_api_key()
        self.timeout_seconds = timeout_seconds

    # 장소 검색어를 받아 Google Places API를 호출하고, 가장 적합한 PlaceResult 객체를 반환
    # 반환: PlaceResult 객체 (장소 ID, 이름, 주소, 좌표, 평점, 리뷰 수)
    # 예외: 장소를 찾지 못하면 ValueError 발생
    def resolve_place(
        self,
        place_name: str,
        language_code: str = "ko",
        region_code: str = "JP",
    ) -> PlaceResult:
        results = self.search_text(
            query=place_name,
            language_code=language_code,
            region_code=region_code,
            max_result_count=1,
        )

        if not results:
            raise ValueError(f"No Google Places result found for: {place_name}")

        return results[0]

    # 실제 Google Places API를 호출하는 핵심 함수
    # query: 검색어
    # language_code: 응답 언어 코드
    # region_code: 검색 지역 코드
    # max_result_count: 최대 검색 결과 개수
    # 반환: PlaceResult 리스트
    def search_text(
        self,
        query: str,
        language_code: str = "ko",
        region_code: str = "JP",
        max_result_count: int = 1,
    ) -> List[PlaceResult]:
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": (
                "places.id,"
                "places.displayName,"
                "places.formattedAddress,"
                "places.location,"
                "places.rating,"
                "places.userRatingCount"
            ),
        }

        payload = {
            "textQuery": query,
            "languageCode": language_code,
            "regionCode": region_code,
            "maxResultCount": max_result_count,
        }

        # Google Places API에 POST 요청 전송
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(self.BASE_URL, headers=headers, json=payload)

        # API 요청 실패 시 상태 코드와 응답 본문을 함께 출력
        if response.status_code >= 400:
            raise RuntimeError(
                "Google Places API request failed: "
                f"status={response.status_code}, body={response.text}"
            )

        data = response.json()
        return [self._parse_place(place) for place in data.get("places", [])]

    # Google 응답 dict 하나를 우리 서비스 모델인 PlaceResult로 변환
    # 예외: 필수값인 장소 ID, 이름, 좌표가 없으면 ValueError 발생
    def _parse_place(self, place: dict) -> PlaceResult:
        display_name = place.get("displayName", {})
        location = place.get("location", {})

        place_id = place.get("id")
        name = display_name.get("text")
        lat = location.get("latitude")
        lng = location.get("longitude")

        if not place_id or not name or lat is None or lng is None:
            raise ValueError(f"Invalid Google Places response: {place}")

        return PlaceResult(
            place_id=place_id,
            name=name,
            formatted_address=place.get("formattedAddress"),
            location=Location(
                name=name,
                lat=lat,
                lng=lng,
            ),
            rating=place.get("rating"),
            review_count=place.get("userRatingCount"),
        )
