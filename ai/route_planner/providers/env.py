# API 키를 환경 변수에서 가져오는 유틸리티 함수
import os
from pathlib import Path

from dotenv import load_dotenv  # env 파일을 그냥 읽는 게 아니라, 환경변수처럼 사용할 수 있게 올려주는 역할


ROUTE_PLANNER_ROOT = Path(__file__).resolve().parents[1]    # ai/route_planner 디렉토리 경로
ROUTE_PLANNER_ENV_PATH = ROUTE_PLANNER_ROOT / ".env"    # ai/route_planner/.env 경로

# ai/route_planner/.env 파일을 읽어 환경변수로 등록하는 함수
def load_route_planner_env() -> None:   
    load_dotenv(ROUTE_PLANNER_ENV_PATH)

# GOOGLE_MAPS_API_KEY를 환경 변수에서 가져오는 함수
def get_google_maps_api_key() -> str:
    load_route_planner_env()

    api_key = os.getenv("GOOGLE_MAPS_API_KEY")

    if not api_key:
        raise ValueError(
            "GOOGLE_MAPS_API_KEY is required. "
            "Check ai/route_planner/.env"
        )

    return api_key
