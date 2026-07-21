# 백엔드와 이미지 장소 검색 모듈이 주고받는 DTO 정의 파일
# (route_planner 의 trip_schemas.py 에 대응하는 계약 파일)
# - 요청: ImageSearchRequest  ← 백엔드 PhotoPlaceSearchRequest 의 상위집합
# - 응답: PlaceCandidate ← 백엔드 PhotoPlaceCandidateRead 에 1:1 매핑 (ImageSearchResult 는 후보 목록을 감싸는 결과 래퍼)
# 내부 모델(원신호·Places 결과)은 domain/schemas.py 에 있다. 의존은 이 파일 → schemas 한 방향만 허용.
from enum import Enum
from typing import Self

from pydantic import BaseModel, Field, model_validator

from ai.image_search.domain.schemas import (
    LandmarkDetection,
    PlaceCategory,
    VisionIdentification,
)


# 후보가 어느 경로로 나왔는지 (랜드마크 식별 / LLM 식별 / 근처 추천)
class CandidateSource(str, Enum):
    LANDMARK = "LANDMARK"
    LLM = "LLM"
    NEARBY = "NEARBY"


# 인식 결과 상태
class RecognitionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


# 사진 장소 검색 요청 (백엔드 PhotoPlaceSearchRequest 의 상위집합)
class ImageSearchRequest(BaseModel):
    image_url: str | None = Field(default=None, min_length=1)  # 호스팅 이미지 URL
    image_path: str | None = Field(default=None, min_length=1)  # 로컬 파일 경로
    note: str | None = Field(default=None, min_length=1)  # 사용자 메모 (예: "야경")
    latitude: float | None = Field(default=None, ge=-90, le=90)  # 촬영/현재 위치 힌트
    longitude: float | None = Field(default=None, ge=-180, le=180)
    city: str | None = Field(default=None, min_length=1)  # 여행 맥락 힌트
    country: str | None = Field(default=None, min_length=1)
    max_candidates: int = Field(default=5, ge=1)  # 반환 후보 최대 개수

    # image_url 또는 image_path 중 최소 하나는 있어야 한다
    @model_validator(mode="after")
    def _require_image_source(self) -> Self:
        if not self.image_url and not self.image_path:
            raise ValueError("image_url 또는 image_path 중 하나는 반드시 필요합니다.")
        return self


# 최종 장소 후보
# 앞쪽은 백엔드 PhotoPlaceCandidateRead에 1:1 매핑되는 계약 필드,
# 뒤쪽은 내부 확장 필드(seam에서 무시)
class PlaceCandidate(BaseModel):
    # --- 백엔드 계약 매핑 필드 ---
    name: str
    city: str
    country: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    confidence: float = Field(ge=0, le=1)
    reason: str
    # --- 내부 분류 필드 ---
    category: PlaceCategory
    source: CandidateSource
    # --- 내부 선택 필드 ---
    place_id: str | None = None
    rating: float | None = Field(default=None, ge=0, le=5)


# 원신호 로깅용 (추후 병렬 앙상블 확장 대비)
class RecognitionSignals(BaseModel):
    landmark: LandmarkDetection | None = None
    llm: VisionIdentification | None = None


# 사진 장소 검색 최종 결과
class ImageSearchResult(BaseModel):
    identified: PlaceCandidate | None  # 식별된 1순위 장소 (실패 시 None)
    candidates: list[PlaceCandidate] = Field(default_factory=list)  # 식별 + 근처 추천
    status: RecognitionStatus
    signals: RecognitionSignals
