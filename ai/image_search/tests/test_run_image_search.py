# scripts/run_image_search.py CLI 검증 — 실제 API 호출 없이 가짜 provider 로 확인
from pathlib import Path

import pytest

from ai.image_search.domain.schemas import (
    LandmarkDetection,
    PlaceCategory,
    ResolvedPlace,
    VisionIdentification,
)
from ai.image_search.scripts.run_image_search import (
    build_recognizer,
    build_request,
    main,
    run_debug,
    run_image_search,
)


# --- 가짜 provider들 (recognizer 테스트와 동일한 형태) ---
class FakeLandmark:
    def __init__(self, result=None, raises=False):
        self.result = result
        self.raises = raises
        self.received_bytes = None

    def detect(self, image_bytes=None, image_url=None):
        self.received_bytes = image_bytes
        if self.raises:
            raise RuntimeError("Cloud Vision API request failed: status=403")
        return self.result


class FakeVision:
    def __init__(self, result=None, raises=False):
        self.result = result
        self.raises = raises

    def identify(self, image_bytes, mime_type="image/jpeg", note=None):
        if self.raises:
            raise RuntimeError("Gemini API error")
        return self.result


class FakePlaces:
    def __init__(self, resolved=None, nearby=None):
        self.resolved = resolved
        self.nearby = nearby if nearby is not None else []
        self.resolve_calls = []

    def resolve_place(self, place_name, language_code="ko", region_code="JP"):
        self.resolve_calls.append(place_name)
        if self.resolved is None:
            raise ValueError(f"No Google Places result found for: {place_name}")
        return self.resolved

    def search_nearby(self, latitude, longitude, category=None, radius_m=1500,
                      max_result_count=5, language_code="ko", region_code="JP"):
        return self.nearby


def landmark_det(name="센소지", score=0.9):
    return LandmarkDetection(name=name, latitude=35.70, longitude=139.79, score=score)


def vision_id(guess="블루보틀", conf=0.8):
    return VisionIdentification(
        place_name_guess=guess, category=PlaceCategory.CAFE, reason="추정", confidence=conf
    )


def resolved_place(name="센소지", pid="p1"):
    return ResolvedPlace(place_id=pid, name=name, latitude=35.7148, longitude=139.7967,
                         city="Tokyo", country="Japan")


# 로컬 사진 파일 하나를 tmp 에 만든다
@pytest.fixture
def photo(tmp_path):
    file = tmp_path / "photo.jpg"
    file.write_bytes(b"\xff\xd8\xff-test-image")
    return file


class TestBuildRequest:
    # 로컬 사진 경로는 절대경로로 정규화되어 요청에 담긴다
    def test_local_path_is_resolved_absolute(self, photo):
        request = build_request(
            image_path=str(photo), image_url=None, note=None, max_candidates=5
        )

        assert request.image_path == str(photo.resolve())
        assert request.image_url is None

    # 메모와 후보 개수가 요청에 반영된다
    def test_note_and_max_candidates(self, photo):
        request = build_request(
            image_path=str(photo), image_url=None, note="야경", max_candidates=3
        )

        assert request.note == "야경"
        assert request.max_candidates == 3


class TestRunImageSearch:
    # 로컬 사진 파일을 실제로 읽어 provider 에 전달한다 (허용 디렉토리 배선 검증)
    def test_reads_local_photo_bytes(self, photo):
        landmark = FakeLandmark(landmark_det())
        recognizer = build_recognizer(
            image_path=photo,
            landmark=landmark,
            vision_llm=FakeVision(vision_id()),
            places=FakePlaces(resolved=resolved_place()),
        )
        request = build_request(
            image_path=str(photo), image_url=None, note=None, max_candidates=2
        )

        payload = run_image_search(request, recognizer)

        assert landmark.received_bytes == b"\xff\xd8\xff-test-image"
        assert payload["status"] in {"SUCCESS", "PARTIAL"}
        assert payload["identified"]["name"] == "센소지"

    # 결과에 원신호(signals)가 포함된다 (실검증 진단용)
    def test_payload_includes_signals(self, photo):
        recognizer = build_recognizer(
            image_path=photo,
            landmark=FakeLandmark(landmark_det()),
            vision_llm=FakeVision(vision_id()),
            places=FakePlaces(resolved=resolved_place()),
        )
        request = build_request(
            image_path=str(photo), image_url=None, note=None, max_candidates=2
        )

        payload = run_image_search(request, recognizer)

        assert payload["signals"]["landmark"]["name"] == "센소지"
        assert payload["signals"]["llm"]["place_name_guess"] == "블루보틀"


class TestRunDebug:
    # provider 오류가 원문 메시지 그대로 보고된다 (캐스케이드가 삼키는 오류 노출)
    def test_reports_provider_error_verbatim(self, photo):
        request = build_request(
            image_path=str(photo), image_url=None, note=None, max_candidates=2
        )

        report = run_debug(
            request,
            image_path=photo,
            landmark=FakeLandmark(raises=True),
            vision_llm=FakeVision(vision_id()),
            places=FakePlaces(resolved=resolved_place()),
        )

        assert report["landmark"]["ok"] is False
        assert "status=403" in report["landmark"]["error"]
        assert report["vision_llm"]["ok"] is True

    # 식별된 장소명이 있으면 좌표 확정까지 진단한다
    def test_resolves_seed_when_identified(self, photo):
        request = build_request(
            image_path=str(photo), image_url=None, note=None, max_candidates=2
        )

        report = run_debug(
            request,
            image_path=photo,
            landmark=FakeLandmark(landmark_det(name="센소지")),
            vision_llm=FakeVision(vision_id()),
            places=FakePlaces(resolved=resolved_place()),
        )

        assert report["places_resolve"]["ok"] is True
        assert report["places_resolve"]["result"]["name"] == "센소지"

    # 약한 랜드마크(score<임계값)면 debug 도 캐스케이드처럼 LLM 추정을 시드로 쓴다
    # (debug 가 캐스케이드 정책을 재사용해 드리프트하지 않는지 검증)
    def test_debug_weak_landmark_uses_llm_seed(self, photo):
        request = build_request(
            image_path=str(photo), image_url=None, note=None, max_candidates=2
        )
        places = FakePlaces(resolved=resolved_place(name="블루보틀"))

        report = run_debug(
            request,
            image_path=photo,
            landmark=FakeLandmark(landmark_det(name="닮은건물", score=0.4)),
            vision_llm=FakeVision(vision_id(guess="블루보틀")),
            places=places,
        )

        # 약한 랜드마크 이름이 아니라 LLM 추정으로 좌표 확정을 시도해야 한다
        assert places.resolve_calls == ["블루보틀"]
        assert report["seed"]["source"] == "LLM"


class TestMain:
    # 존재하지 않는 사진 경로면 실패 코드 1 을 반환한다
    # (provider 는 가짜 키로 생성되게 해, 실패 지점이 파일 로딩임을 보장)
    def test_returns_failure_for_missing_photo(self, monkeypatch, tmp_path):
        monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "dummy")
        monkeypatch.setenv("GOOGLE_CLOUD_VISION_API_KEY", "dummy")
        monkeypatch.setenv("GEMINI_API_KEY", "dummy")
        monkeypatch.setattr(
            "sys.argv",
            ["run_image_search", "--image-path", str(tmp_path / "missing.jpg")],
        )

        assert main() == 1
