# 여러 테스트가 공유하는 가짜 provider 와 빌더 (Protocol 만족, 호출 기록 포함)
# 실제 provider 대신 주입해 네트워크·API 키 없이 캐스케이드·CLI 를 검증한다.
from ai.image_search.domain.schemas import (
    LandmarkDetection,
    PlaceCategory,
    ResolvedPlace,
    VisionIdentification,
)


class FakeLandmark:
    def __init__(self, result=None, raises=False):
        self.result = result
        self.raises = raises
        self.calls = []
        self.received_bytes = None

    def detect(self, image_bytes=None, image_url=None):
        self.calls.append(image_bytes)
        self.received_bytes = image_bytes
        if self.raises:
            raise RuntimeError("Cloud Vision API 요청 실패: status=403")
        return self.result


class FakeVision:
    def __init__(self, result=None, raises=False):
        self.result = result
        self.raises = raises
        self.calls = []
        self.mime_types = []

    def identify(self, image_bytes, mime_type="image/jpeg", note=None):
        self.calls.append((image_bytes, note))
        self.mime_types.append(mime_type)
        if self.raises:
            raise RuntimeError("Gemini API 오류")
        return self.result


class FakePlaces:
    # resolve_map 이 주어지면 이름별로 조회 (없는 이름은 ValueError) — 시드별 성공/실패를 구분
    def __init__(self, resolved=None, resolve_raises=False, nearby=None,
                 nearby_raises=False, resolve_map=None):
        self.resolved = resolved
        self.resolve_raises = resolve_raises
        self.resolve_map = resolve_map
        self.nearby = nearby if nearby is not None else []
        self.nearby_raises = nearby_raises
        self.resolve_calls = []
        self.nearby_calls = []

    def resolve_place(self, place_name, language_code="ko", region_code="JP"):
        self.resolve_calls.append(place_name)
        if self.resolve_raises:
            raise ValueError("검색 결과 없음")
        if self.resolve_map is not None:
            if place_name not in self.resolve_map:
                raise ValueError(f"검색 결과 없음: {place_name}")
            return self.resolve_map[place_name]
        return self.resolved

    def search_nearby(self, latitude, longitude, category=None, radius_m=1500,
                      max_result_count=5, language_code="ko", region_code="JP"):
        self.nearby_calls.append(
            {"lat": latitude, "lng": longitude,
             "category": category, "max": max_result_count}
        )
        if self.nearby_raises:
            raise RuntimeError("근처 검색 실패")
        return self.nearby


# --- 빌더 ---
def landmark_det(name="센소지", lat=35.70, lng=139.70, score=0.9):
    return LandmarkDetection(name=name, latitude=lat, longitude=lng, score=score)


def vision_id(guess="블루보틀", cat=PlaceCategory.CAFE, conf=0.8):
    return VisionIdentification(
        place_name_guess=guess, category=cat, reason="추정", confidence=conf
    )


def resolved_place(name="센소지", lat=35.7148, lng=139.7967, city="Tokyo",
                   country="Japan", pid="p1", rating=4.5):
    return ResolvedPlace(place_id=pid, name=name, latitude=lat, longitude=lng,
                         city=city, country=country, rating=rating)
