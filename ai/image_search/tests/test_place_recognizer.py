# services/place_recognizer.py 테스트 — 캐스케이드 조립 로직
# 실제 provider 대신 가짜 provider(Protocol 만족)를 주입해 분기·상태·좌표 출처를 검증
from ai.image_search.domain.schemas import (
    LandmarkDetection,
    PlaceCategory,
    ResolvedPlace,
    VisionIdentification,
)
from ai.image_search.domain.search_schemas import (
    CandidateSource,
    ImageSearchRequest,
    RecognitionStatus,
)
from ai.image_search.services.place_recognizer import (
    PlaceRecognizer,
    PlaceRecognizerConfig,
)


# --- 가짜 provider들 (호출 기록 포함) ---
class FakeLandmark:
    def __init__(self, result=None, raises=False):
        self.result = result
        self.raises = raises
        self.calls = []

    def detect(self, image_bytes=None, image_url=None):
        self.calls.append(image_bytes)
        if self.raises:
            raise RuntimeError("vision down")
        return self.result


class FakeVision:
    def __init__(self, result=None, raises=False):
        self.result = result
        self.raises = raises
        self.calls = []

    def identify(self, image_bytes, mime_type="image/jpeg", note=None):
        self.calls.append((image_bytes, note))
        if self.raises:
            raise RuntimeError("gemini down")
        return self.result


class FakePlaces:
    def __init__(self, resolved=None, resolve_raises=False, nearby=None, nearby_raises=False):
        self.resolved = resolved
        self.resolve_raises = resolve_raises
        self.nearby = nearby if nearby is not None else []
        self.nearby_raises = nearby_raises
        self.resolve_calls = []
        self.nearby_calls = []

    def resolve_place(self, place_name, language_code="ko", region_code="JP"):
        self.resolve_calls.append(place_name)
        if self.resolve_raises:
            raise ValueError("no result")
        return self.resolved

    def search_nearby(self, latitude, longitude, category=None, radius_m=1500,
                      max_result_count=5, language_code="ko", region_code="JP"):
        self.nearby_calls.append(
            {"lat": latitude, "lng": longitude, "category": category, "max": max_result_count}
        )
        if self.nearby_raises:
            raise RuntimeError("places nearby down")
        return self.nearby


# --- 빌더 ---
def landmark_det(name="센소지", lat=35.70, lng=139.70, score=0.9):
    return LandmarkDetection(name=name, latitude=lat, longitude=lng, score=score)


def vision_id(guess="블루보틀", cat=PlaceCategory.CAFE, conf=0.8):
    return VisionIdentification(place_name_guess=guess, category=cat, reason="추정", confidence=conf)


def resolved_place(name="센소지", lat=35.7148, lng=139.7967, city="Tokyo",
                   country="Japan", pid="p1", rating=4.5):
    return ResolvedPlace(place_id=pid, name=name, latitude=lat, longitude=lng,
                         city=city, country=country, rating=rating)


def make_recognizer(landmark, vision, places, **cfg):
    return PlaceRecognizer(
        landmark=landmark,
        vision_llm=vision,
        places=places,
        config=PlaceRecognizerConfig(**cfg) if cfg else None,
        image_loader=lambda req: b"fake-image-bytes",
    )


def req(**kw):
    base = dict(image_url="https://x/a.jpg", max_candidates=5)
    base.update(kw)
    return ImageSearchRequest(**base)


class TestCascade:
    # 자신 있는 랜드마크(score≥임계값) → 랜드마크 채택, 근처 추천 있음 → SUCCESS
    def test_confident_landmark_success(self):
        places = FakePlaces(resolved=resolved_place(), nearby=[resolved_place(name="근처1", pid="n1")])
        rec = make_recognizer(FakeLandmark(landmark_det(score=0.93)), FakeVision(vision_id()), places)

        result = rec.search(req())

        assert result.status is RecognitionStatus.SUCCESS
        assert result.identified.source is CandidateSource.LANDMARK
        assert result.identified.confidence == 0.93
        assert len(result.candidates) == 2  # 식별 + 근처 1
        assert result.candidates[1].source is CandidateSource.NEARBY
        # 랜드마크 이름으로 좌표를 확정하러 갔는가
        assert places.resolve_calls == ["센소지"]

    # 약한 랜드마크(score<임계값) → Gemini 추정으로 폴백
    def test_weak_landmark_falls_back_to_llm(self):
        places = FakePlaces(resolved=resolved_place(name="블루보틀"), nearby=[])
        rec = make_recognizer(
            FakeLandmark(landmark_det(name="닮은건물", score=0.4)),
            FakeVision(vision_id(guess="블루보틀 교토점")),
            places,
        )

        result = rec.search(req())

        assert result.identified.source is CandidateSource.LLM
        assert places.resolve_calls == ["블루보틀 교토점"]  # 랜드마크가 아닌 LLM 추정으로

    # 랜드마크 감지 없음 → Gemini 경로
    def test_no_landmark_uses_llm(self):
        places = FakePlaces(resolved=resolved_place(), nearby=[])
        rec = make_recognizer(FakeLandmark(None), FakeVision(vision_id(guess="어딘가")), places)

        result = rec.search(req())

        assert result.identified.source is CandidateSource.LLM

    # 랜드마크도 없고 LLM 장소명 추정도 없음 → FAILED (빈 후보)
    def test_no_seed_returns_failed(self):
        rec = make_recognizer(
            FakeLandmark(None),
            FakeVision(vision_id(guess=None)),  # 특정 못 함
            FakePlaces(resolved=resolved_place()),
        )

        result = rec.search(req())

        assert result.status is RecognitionStatus.FAILED
        assert result.identified is None
        assert result.candidates == []

    # 식별 성공 + 근처 검색 결과 없음 → PARTIAL
    def test_nearby_empty_returns_partial(self):
        rec = make_recognizer(
            FakeLandmark(landmark_det(score=0.9)),
            FakeVision(vision_id()),
            FakePlaces(resolved=resolved_place(), nearby=[]),
        )

        result = rec.search(req())

        assert result.status is RecognitionStatus.PARTIAL
        assert len(result.candidates) == 1

    # 좌표 확정(Places resolve) 실패 → FAILED (그라운딩 불가)
    def test_resolve_failure_returns_failed(self):
        rec = make_recognizer(
            FakeLandmark(landmark_det(score=0.9)),
            FakeVision(vision_id()),
            FakePlaces(resolve_raises=True),
        )

        result = rec.search(req())

        assert result.status is RecognitionStatus.FAILED
        assert result.identified is None

    # 랜드마크 provider 예외 → LLM 으로 우아하게 폴백
    def test_landmark_exception_falls_back_to_llm(self):
        places = FakePlaces(resolved=resolved_place(), nearby=[])
        rec = make_recognizer(FakeLandmark(raises=True), FakeVision(vision_id(guess="카페")), places)

        result = rec.search(req())

        assert result.identified.source is CandidateSource.LLM

    # LLM 예외 + 랜드마크 성공 → 랜드마크로 진행, 근처 검색은 카테고리 필터 없이
    def test_llm_exception_proceeds_with_landmark(self):
        places = FakePlaces(resolved=resolved_place(), nearby=[resolved_place(name="근처", pid="n1")])
        rec = make_recognizer(FakeLandmark(landmark_det(score=0.9)), FakeVision(raises=True), places)

        result = rec.search(req())

        assert result.identified.source is CandidateSource.LANDMARK
        assert places.nearby_calls[0]["category"] is None  # LLM 없으니 카테고리 미지정

    # 좌표는 항상 Places 실제값 (랜드마크가 준 좌표를 신뢰하지 않음)
    def test_coordinates_always_from_places(self):
        places = FakePlaces(resolved=resolved_place(lat=35.7148, lng=139.7967), nearby=[])
        rec = make_recognizer(
            FakeLandmark(landmark_det(lat=35.00, lng=139.00, score=0.9)),  # 다른 좌표
            FakeVision(vision_id()),
            places,
        )

        result = rec.search(req())

        assert result.identified.latitude == 35.7148  # 랜드마크(35.0)가 아닌 Places
        assert result.identified.longitude == 139.7967

    # 원신호(landmark·llm)가 결과에 보존된다
    def test_signals_preserved(self):
        rec = make_recognizer(
            FakeLandmark(landmark_det(score=0.9)),
            FakeVision(vision_id()),
            FakePlaces(resolved=resolved_place(), nearby=[]),
        )

        result = rec.search(req())

        assert result.signals.landmark is not None
        assert result.signals.llm is not None

    # max_candidates 가 근처 검색 개수를 제한한다 (식별 1 + 근처 N-1, 자기자신 제외 대비 +1)
    def test_max_candidates_limits_nearby(self):
        places = FakePlaces(resolved=resolved_place(), nearby=[])
        rec = make_recognizer(FakeLandmark(landmark_det(score=0.9)), FakeVision(vision_id()), places)

        rec.search(req(max_candidates=3))

        assert places.nearby_calls[0]["max"] == 3  # (3 - 1) + 1(자기자신 제외 대비)

    # max_candidates=1 이면 근처 검색을 아예 하지 않고 식별만 반환 (PARTIAL)
    def test_max_candidates_one_skips_nearby(self):
        places = FakePlaces(resolved=resolved_place(), nearby=[resolved_place(name="근처", pid="n1")])
        rec = make_recognizer(FakeLandmark(landmark_det(score=0.9)), FakeVision(vision_id()), places)

        result = rec.search(req(max_candidates=1))

        assert places.nearby_calls == []  # 근처 검색 호출 자체를 안 함
        assert len(result.candidates) == 1
        assert result.status is RecognitionStatus.PARTIAL

    # 근처 검색(Places) 예외 → 식별만 반환 (PARTIAL, 우아한 저하)
    def test_nearby_exception_returns_partial(self):
        rec = make_recognizer(
            FakeLandmark(landmark_det(score=0.9)),
            FakeVision(vision_id()),
            FakePlaces(resolved=resolved_place(), nearby_raises=True),
        )

        result = rec.search(req())

        assert result.status is RecognitionStatus.PARTIAL
        assert len(result.candidates) == 1
        assert result.identified is not None

    # 근처 검색 결과에 식별 장소 자신이 섞여 오면 제외한다 (place_id 기준 중복 방지)
    def test_excludes_identified_place_from_nearby(self):
        nearby = [
            resolved_place(name="센소지", pid="p1"),  # 식별 장소 자신 (같은 place_id)
            resolved_place(name="근처1", pid="n1"),
        ]
        places = FakePlaces(resolved=resolved_place(pid="p1"), nearby=nearby)
        rec = make_recognizer(FakeLandmark(landmark_det(score=0.9)), FakeVision(vision_id()), places)

        result = rec.search(req())

        ids = [c.place_id for c in result.candidates]
        assert ids.count("p1") == 1  # 식별로 한 번만 등장
        assert "n1" in ids

    # 자기 자신 제외 후에도 요청 개수를 초과하지 않게 wanted 로 자른다
    def test_truncates_nearby_to_wanted_after_filter(self):
        nearby = [resolved_place(name=f"근처{i}", pid=f"n{i}") for i in range(5)]
        places = FakePlaces(resolved=resolved_place(pid="p1"), nearby=nearby)
        rec = make_recognizer(FakeLandmark(landmark_det(score=0.9)), FakeVision(vision_id()), places)

        result = rec.search(req(max_candidates=5))

        assert len(result.candidates) == 5  # 식별 1 + 근처 4 (5개 중 1개 잘림)

    # 근처 검색 요청 개수는 Places API 상한(20)을 넘지 않는다
    def test_nearby_fetch_respects_places_api_cap(self):
        places = FakePlaces(resolved=resolved_place(), nearby=[])
        rec = make_recognizer(FakeLandmark(landmark_det(score=0.9)), FakeVision(vision_id()), places)

        rec.search(req(max_candidates=25))

        assert places.nearby_calls[0]["max"] == 20  # (25-1)+1=25 → 상한 20

    # 근처 추천 confidence 는 식별보다 낮게 점감한다
    def test_nearby_confidence_decays(self):
        nearby = [resolved_place(name=f"근처{i}", pid=f"n{i}") for i in range(3)]
        rec = make_recognizer(
            FakeLandmark(landmark_det(score=0.9)), FakeVision(vision_id()),
            FakePlaces(resolved=resolved_place(), nearby=nearby),
        )

        result = rec.search(req())

        confs = [c.confidence for c in result.candidates]
        assert confs[0] == 0.9  # 식별
        assert confs[1] > confs[2] > confs[3]  # 근처는 순차 감소
        assert all(0 <= c <= 1 for c in confs)
