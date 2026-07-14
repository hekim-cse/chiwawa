# API 키를 환경 변수에서 가져오는 유틸리티 (ai/image_search/.env 로딩)
# .env 를 그냥 읽는 게 아니라 환경변수처럼 사용할 수 있게 올려주는 역할
import os
from pathlib import Path

from dotenv import load_dotenv


IMAGE_SEARCH_ROOT = Path(__file__).resolve().parents[1]  # ai/image_search 디렉토리 경로
IMAGE_SEARCH_ENV_PATH = IMAGE_SEARCH_ROOT / ".env"  # ai/image_search/.env 경로


# ai/image_search/.env 파일을 읽어 환경변수로 등록하는 함수
def load_image_search_env() -> None:
    load_dotenv(IMAGE_SEARCH_ENV_PATH)


# 지정한 환경변수를 읽어 반환하고, 없거나 비어 있으면 즉시 실패(fail-fast)하는 헬퍼
def _require_env(var_name: str) -> str:
    load_image_search_env()

    value = os.getenv(var_name)

    if not value:
        raise ValueError(
            f"{var_name} is required. Check ai/image_search/.env"
        )

    return value


# Google Places API 키 (장소명 → 좌표/근처 검색)
def get_google_maps_api_key() -> str:
    return _require_env("GOOGLE_MAPS_API_KEY")


# Google Cloud Vision API 키 (랜드마크 감지, REST 호출)
def get_google_cloud_vision_api_key() -> str:
    return _require_env("GOOGLE_CLOUD_VISION_API_KEY")


# Google Gemini API 키 (비전 LLM, AI Studio)
def get_gemini_api_key() -> str:
    return _require_env("GEMINI_API_KEY")
