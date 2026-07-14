# providers/landmark_provider.py 테스트
# httpx MockTransport 로 실제 네트워크 없이 요청 생성·응답 파싱을 검증
import base64
import json

import httpx
import pytest

from ai.image_search.providers.landmark_provider import LandmarkProvider


# 주어진 핸들러로 MockTransport 를 붙인 LandmarkProvider 를 만든다
def make_provider(handler) -> LandmarkProvider:
    return LandmarkProvider(api_key="test-key", transport=httpx.MockTransport(handler))


# Vision 랜드마크 annotation 하나를 만드는 헬퍼
def landmark_annotation(**overrides) -> dict:
    annotation = {
        "description": "Sensō-ji",
        "score": 0.93,
        "locations": [
            {"latLng": {"latitude": 35.7148, "longitude": 139.7967}},
        ],
    }
    annotation.update(overrides)
    return annotation


class TestDetect:
    # 이미지 URL 로 랜드마크를 감지한다 (요청 형태·응답 파싱 모두 검증)
    def test_detects_landmark_from_image_url(self):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["path"] = request.url.path
            captured["api_key"] = request.headers.get("X-Goog-Api-Key")
            captured["body"] = json.loads(request.content)
            return httpx.Response(
                200,
                json={"responses": [{"landmarkAnnotations": [landmark_annotation()]}]},
            )

        provider = make_provider(handler)
        detection = provider.detect(image_url="https://example.com/asakusa.jpg")

        # 응답 파싱 검증
        assert detection is not None
        assert detection.name == "Sensō-ji"
        assert detection.score == 0.93
        assert detection.latitude == 35.7148
        assert detection.longitude == 139.7967
        # 요청 생성 검증
        assert captured["path"].endswith("/v1/images:annotate")
        assert captured["api_key"] == "test-key"
        request_entry = captured["body"]["requests"][0]
        assert request_entry["image"]["source"]["imageUri"] == "https://example.com/asakusa.jpg"
        assert request_entry["features"][0]["type"] == "LANDMARK_DETECTION"

    # 이미지 바이트는 base64 로 인코딩해 전송한다
    def test_sends_image_bytes_as_base64(self):
        captured = {}
        raw = b"fake-jpeg-bytes"

        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return httpx.Response(
                200,
                json={"responses": [{"landmarkAnnotations": [landmark_annotation()]}]},
            )

        provider = make_provider(handler)
        detection = provider.detect(image_bytes=raw)

        assert detection is not None
        sent = captured["body"]["requests"][0]["image"]["content"]
        assert base64.b64decode(sent) == raw

    # 이미지 소스가 하나도 없으면 ValueError (요청 자체를 만들지 않음)
    def test_requires_at_least_one_image_source(self):
        provider = make_provider(lambda request: httpx.Response(200, json={}))

        with pytest.raises(ValueError):
            provider.detect()

    # 랜드마크가 감지되지 않으면 None (예외 아님 — 캐스케이드가 LLM 으로 폴백할 근거)
    def test_returns_none_when_no_landmark(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"responses": [{}]})

        provider = make_provider(handler)

        assert provider.detect(image_url="https://x/cafe.jpg") is None

    # 좌표 없는 annotation 은 건너뛰고 다음 유효한 것을 쓴다
    def test_skips_annotation_without_coordinates(self):
        no_coords = landmark_annotation(description="좌표 없는 곳", locations=[])

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "responses": [
                        {"landmarkAnnotations": [no_coords, landmark_annotation()]}
                    ]
                },
            )

        provider = make_provider(handler)
        detection = provider.detect(image_url="https://x/a.jpg")

        assert detection is not None
        assert detection.name == "Sensō-ji"

    # responses 배열이 완전히 비어 있어도 None (인덱스 접근 전 가드)
    def test_returns_none_when_responses_empty(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"responses": []})

        provider = make_provider(handler)

        assert provider.detect(image_url="https://x/a.jpg") is None

    # 유효한 annotation 이 하나도 없으면 None
    def test_returns_none_when_no_valid_annotation(self):
        no_coords = landmark_annotation(locations=[])

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, json={"responses": [{"landmarkAnnotations": [no_coords]}]}
            )

        provider = make_provider(handler)

        assert provider.detect(image_url="https://x/a.jpg") is None

    # Vision 은 HTTP 200 안에 error 객체를 심어 보낼 수 있다 → RuntimeError
    def test_raises_on_embedded_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "responses": [
                        {"error": {"code": 7, "message": "PERMISSION_DENIED"}}
                    ]
                },
            )

        provider = make_provider(handler)
        with pytest.raises(RuntimeError):
            provider.detect(image_url="https://x/a.jpg")

    # HTTP 오류(4xx/5xx)면 RuntimeError
    def test_raises_on_http_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(403, json={"error": "forbidden"})

        provider = make_provider(handler)
        with pytest.raises(RuntimeError):
            provider.detect(image_url="https://x/a.jpg")
