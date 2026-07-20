# providers/vision_llm_provider.py 테스트
# 실제 google-genai SDK·네트워크 없이, 가짜 client 를 주입해 검증
import json

import pytest
from pydantic import ValidationError

from ai.image_search.domain.schemas import PlaceCategory
from ai.image_search.providers.vision_llm_provider import VisionLlmProvider


# --- 가짜 genai client (client.models.generate_content 만 흉내) ---
class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeModels:
    def __init__(self, response_text: str, capture: dict) -> None:
        self._response_text = response_text
        self._capture = capture

    def generate_content(self, *, model, contents, config):
        self._capture["model"] = model
        self._capture["contents"] = contents
        self._capture["config"] = config
        return _FakeResponse(self._response_text)


class _FakeClient:
    def __init__(self, response_text: str, capture: dict) -> None:
        self.models = _FakeModels(response_text, capture)


# 유효한 Gemini JSON 응답 하나
def valid_response(**overrides) -> str:
    payload = {
        "place_name_guess": "블루보틀 교토점",
        "category": "CAFE",
        "vibe_keywords": ["미니멀", "우드톤"],
        "reason": "간판과 인테리어로 추정",
        "confidence": 0.82,
        "visible_text": ["BLUE BOTTLE COFFEE"],
    }
    payload.update(overrides)
    return json.dumps(payload, ensure_ascii=False)


# 주어진 응답으로 provider + capture 를 만든다
def make_provider(response_text: str):
    capture: dict = {}
    provider = VisionLlmProvider(
        api_key="test-key", client=_FakeClient(response_text, capture)
    )
    return provider, capture


class TestIdentify:
    # 이미지 바이트로 식별하고, 응답 JSON 을 VisionIdentification 으로 파싱한다
    def test_identifies_and_parses_response(self):
        provider, capture = make_provider(valid_response())

        result = provider.identify(image_bytes=b"jpeg-bytes", note="예쁜 카페")

        assert result.place_name_guess == "블루보틀 교토점"
        assert result.category is PlaceCategory.CAFE
        assert result.confidence == 0.82
        assert result.visible_text == ["BLUE BOTTLE COFFEE"]
        assert "미니멀" in result.vibe_keywords

    # 요청에 구조화 출력 설정(JSON + response_schema)과 이미지가 실린다
    def test_request_uses_structured_output_and_image(self):
        provider, capture = make_provider(valid_response())

        provider.identify(image_bytes=b"jpeg-bytes", note="야경")

        config = capture["config"]
        assert config.response_mime_type == "application/json"
        assert config.response_schema is not None
        # contents 에 이미지 파트가 실렸는지 (bytes 보존)
        contents = capture["contents"]
        assert any(getattr(getattr(p, "inline_data", None), "data", None) == b"jpeg-bytes"
                   for p in contents if not isinstance(p, str))

    # 사용자 메모(note)가 프롬프트에 반영된다
    def test_note_is_included_in_prompt(self):
        provider, capture = make_provider(valid_response())

        provider.identify(image_bytes=b"x", note="한적한 골목 카페")

        prompt_texts = [p for p in capture["contents"] if isinstance(p, str)]
        assert any("한적한 골목 카페" in t for t in prompt_texts)

    # LLM 이 범위 밖 confidence 를 주면 방어적으로 거부한다 (재검증)
    def test_rejects_out_of_range_confidence_from_llm(self):
        provider, _ = make_provider(valid_response(confidence=1.7))

        with pytest.raises(ValidationError):
            provider.identify(image_bytes=b"x")

    # LLM 이 정의되지 않은 카테고리를 주면 거부한다 (폐집합 강제)
    def test_rejects_unknown_category_from_llm(self):
        provider, _ = make_provider(valid_response(category="SPACESHIP"))

        with pytest.raises(ValidationError):
            provider.identify(image_bytes=b"x")

    # place_name_guess 가 없어도(일반 분위기) 유효하게 파싱된다
    def test_allows_missing_place_name_guess(self):
        provider, _ = make_provider(
            valid_response(place_name_guess=None, visible_text=[])
        )

        result = provider.identify(image_bytes=b"x")

        assert result.place_name_guess is None
        assert result.category is PlaceCategory.CAFE
