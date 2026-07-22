# Google Places API를 호출해서 "장소명"을 "좌표/주소/평점 정보"로 변환하고
# 좌표 주변의 유사 장소를 검색하는 Provider
import httpx

from ai.image_search.domain.schemas import PlaceCategory, ResolvedPlace
from ai.image_search.providers.env import get_google_maps_api_key


# 우리 카테고리 -> Google Places includedTypes 매핑 (근처 검색 필터용)
# 값이 빈 리스트면 필터 없이 검색한다. 실제 호출 검증(CLI) 단계에서 타입 유효성을 조정한다.
CATEGORY_INCLUDED_TYPES: dict[PlaceCategory, list[str]] = {
    PlaceCategory.LANDMARK: ["tourist_attraction"],
    PlaceCategory.TEMPLE_SHRINE: ["tourist_attraction"],
    PlaceCategory.HISTORIC: ["historical_landmark"],
    PlaceCategory.MUSEUM: ["museum"],
    PlaceCategory.GALLERY: ["art_gallery"],
    PlaceCategory.ARCHITECTURE: ["tourist_attraction"],
    PlaceCategory.NATURE: ["park", "national_park"],
    PlaceCategory.PARK: ["park"],
    PlaceCategory.GARDEN: ["botanical_garden"],
    PlaceCategory.BEACH: ["tourist_attraction"],
    PlaceCategory.VIEWPOINT: ["tourist_attraction"],
    PlaceCategory.NIGHTVIEW: ["tourist_attraction"],
    PlaceCategory.ONSEN: ["spa"],
    PlaceCategory.CAFE: ["cafe"],
    PlaceCategory.RESTAURANT: ["restaurant"],
    PlaceCategory.DESSERT: ["bakery"],
    PlaceCategory.BAR: ["bar"],
    PlaceCategory.MARKET: ["market"],
    PlaceCategory.SHOPPING: ["shopping_mall"],
    PlaceCategory.STREET: ["tourist_attraction"],
    PlaceCategory.THEME_PARK: ["amusement_park"],
    PlaceCategory.AQUARIUM_ZOO: ["aquarium", "zoo"],
    PlaceCategory.ETC: [],
}


# Google Places API 를 감싸 장소명 -> ResolvedPlace 로 변환하는 Provider
class PlacesProvider:
    SEARCH_TEXT_URL = "https://places.googleapis.com/v1/places:searchText"
    SEARCH_NEARBY_URL = "https://places.googleapis.com/v1/places:searchNearby"

    # api_key: Google Places API 키 (없으면 환경변수에서 가져옴)
    # timeout_seconds: API 호출 타임아웃 (초)
    # transport: httpx 전송 계층 주입용 (테스트에서 MockTransport, 실제 사용 시 None)
    def __init__(
        self,
        api_key: str | None = None,
        timeout_seconds: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.api_key = api_key or get_google_maps_api_key()
        self.timeout_seconds = timeout_seconds
        self._transport = transport

    # 내부 httpx 클라이언트 생성 (주입된 transport 가 있으면 그것을 사용)
    def _client(self) -> httpx.Client:
        return httpx.Client(timeout=self.timeout_seconds, transport=self._transport)

    # 장소명을 받아 가장 적합한 ResolvedPlace 하나를 반환
    # 예외: 결과가 없으면 ValueError
    def resolve_place(
        self,
        place_name: str,
        language_code: str = "ko",
        region_code: str = "JP",
    ) -> ResolvedPlace:
        results = self.search_text(
            query=place_name,
            language_code=language_code,
            region_code=region_code,
            max_result_count=1,
        )

        if not results:
            raise ValueError(f"Google Places 검색 결과가 없습니다: {place_name}")

        return results[0]

    # 실제 Places Text Search 를 호출하고 ResolvedPlace 리스트를 반환
    def search_text(
        self,
        query: str,
        language_code: str = "ko",
        region_code: str = "JP",
        max_result_count: int = 1,
    ) -> list[ResolvedPlace]:
        payload = {
            "textQuery": query,
            "languageCode": language_code,
            "regionCode": region_code,
            "maxResultCount": max_result_count,
        }

        return self._post_and_parse(self.SEARCH_TEXT_URL, payload)

    # 좌표 주변에서 카테고리에 맞는 장소를 검색한다 (근처 추천용)
    # category 가 None 이거나 매핑이 비어 있으면 유형 필터 없이 검색한다
    # 결과가 없으면 빈 리스트를 반환한다 (resolve_place 와 달리 예외 아님)
    def search_nearby(
        self,
        latitude: float,
        longitude: float,
        category: PlaceCategory | None = None,
        radius_m: float = 1500,
        max_result_count: int = 5,
        language_code: str = "ko",
        region_code: str = "JP",
    ) -> list[ResolvedPlace]:
        payload: dict = {
            "languageCode": language_code,
            "regionCode": region_code,
            "maxResultCount": max_result_count,
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": latitude, "longitude": longitude},
                    "radius": radius_m,
                },
            },
        }

        included_types = CATEGORY_INCLUDED_TYPES.get(category) if category else None
        if included_types:
            payload["includedTypes"] = included_types

        return self._post_and_parse(self.SEARCH_NEARBY_URL, payload)

    # 공통 요청 처리: 헤더 구성 → POST → 오류 확인 → places 파싱
    def _post_and_parse(self, url: str, payload: dict) -> list[ResolvedPlace]:
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": (
                "places.id,"
                "places.displayName,"
                "places.formattedAddress,"
                "places.addressComponents,"
                "places.location,"
                "places.rating,"
                "places.userRatingCount,"
                "places.primaryType"
            ),
        }

        with self._client() as client:
            response = client.post(url, headers=headers, json=payload)

        # API 요청 실패 시 상태 코드와 응답 본문을 함께 알린다
        if response.status_code >= 400:
            raise RuntimeError(
                "Google Places API 요청 실패: "
                f"status={response.status_code}, body={response.text}"
            )

        data = response.json()
        return [self._parse_place(place) for place in data.get("places", [])]

    # Google 응답 dict 하나를 ResolvedPlace 로 변환
    # 예외: 필수값(장소 ID, 이름, 좌표)이 없으면 ValueError
    def _parse_place(self, place: dict) -> ResolvedPlace:
        display_name = place.get("displayName", {})
        location = place.get("location", {})

        place_id = place.get("id")
        name = display_name.get("text")
        lat = location.get("latitude")
        lng = location.get("longitude")

        if not place_id or not name or lat is None or lng is None:
            raise ValueError(f"유효하지 않은 Google Places 응답입니다: {place}")

        city, country = self._parse_address_components(
            place.get("addressComponents", [])
        )

        return ResolvedPlace(
            place_id=place_id,
            name=name,
            latitude=lat,
            longitude=lng,
            formatted_address=place.get("formattedAddress"),
            city=city,
            country=country,
            rating=place.get("rating"),
            review_count=place.get("userRatingCount"),
            primary_type=place.get("primaryType"),
        )

    # addressComponents 에서 도시/국가를 구조화 파싱
    # 도시: locality 우선, 없으면 administrative_area_level_1 로 폴백 (없으면 None)
    @staticmethod
    def _parse_address_components(
        components: list[dict],
    ) -> tuple[str | None, str | None]:
        locality: str | None = None
        admin_area: str | None = None
        country: str | None = None

        for component in components:
            types = component.get("types", [])
            text = (component.get("longText") or "").strip() or None
            if text is None:
                continue
            if "locality" in types and locality is None:
                locality = text
            elif "administrative_area_level_1" in types and admin_area is None:
                admin_area = text
            elif "country" in types and country is None:
                country = text

        return locality or admin_area, country
