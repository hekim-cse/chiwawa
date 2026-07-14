# providers/env.py 의 API 키 getter 동작 테스트 (실제 .env 파일에 의존하지 않음)
import pytest

from ai.image_search.providers import env


# .env 파일 로딩을 무력화해 테스트를 결정론적으로 만든다
# (개발자 로컬에 .env 가 있어도 테스트 결과가 흔들리지 않게)
@pytest.fixture(autouse=True)
def _disable_dotenv(monkeypatch):
    monkeypatch.setattr(env, "load_image_search_env", lambda: None)


class TestApiKeyGetters:
    # 환경변수가 설정돼 있으면 그 값을 반환한다
    def test_returns_gemini_key_when_set(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "gemini-test-key")

        assert env.get_gemini_api_key() == "gemini-test-key"

    def test_returns_maps_key_when_set(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "maps-test-key")

        assert env.get_google_maps_api_key() == "maps-test-key"

    def test_returns_vision_key_when_set(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_CLOUD_VISION_API_KEY", "vision-test-key")

        assert env.get_google_cloud_vision_api_key() == "vision-test-key"

    # 환경변수가 없으면 ValueError 로 즉시 실패한다 (fail-fast)
    def test_raises_when_gemini_key_missing(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)

        with pytest.raises(ValueError):
            env.get_gemini_api_key()

    def test_raises_when_maps_key_missing(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)

        with pytest.raises(ValueError):
            env.get_google_maps_api_key()

    def test_raises_when_vision_key_missing(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_CLOUD_VISION_API_KEY", raising=False)

        with pytest.raises(ValueError):
            env.get_google_cloud_vision_api_key()

    # 빈 문자열도 미설정으로 간주해 실패한다
    def test_raises_when_key_is_empty_string(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "")

        with pytest.raises(ValueError):
            env.get_gemini_api_key()
