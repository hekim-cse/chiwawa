# 데이터 구조 정의 파일 (사진 기반 장소 식별/추천의 요청·후보·결과 모델)
from enum import Enum
from typing import Self

from pydantic import BaseModel, Field, model_validator


# 장소 카테고리 (사진 기반 식별 + 근처 추천 필터용 택소노미)
class PlaceCategory(str, Enum):
    # 명소·역사·문화
    LANDMARK = "LANDMARK"  # 랜드마크·명소
    TEMPLE_SHRINE = "TEMPLE_SHRINE"  # 사찰·신사
    HISTORIC = "HISTORIC"  # 유적·역사지구·성(城)
    MUSEUM = "MUSEUM"  # 박물관
    GALLERY = "GALLERY"  # 미술관·갤러리
    ARCHITECTURE = "ARCHITECTURE"  # 건축물·근대건축
    # 자연·풍경
    NATURE = "NATURE"  # 자연·산·숲
    PARK = "PARK"  # 공원
    GARDEN = "GARDEN"  # 정원
    BEACH = "BEACH"  # 해변·바다
    VIEWPOINT = "VIEWPOINT"  # 전망대·뷰포인트
    NIGHTVIEW = "NIGHTVIEW"  # 야경
    ONSEN = "ONSEN"  # 온천
    # 음식·카페
    CAFE = "CAFE"  # 카페
    RESTAURANT = "RESTAURANT"  # 음식점
    DESSERT = "DESSERT"  # 디저트·베이커리
    BAR = "BAR"  # 바·이자카야
    MARKET = "MARKET"  # 시장·먹자골목
    # 활동·쇼핑·거리
    SHOPPING = "SHOPPING"  # 쇼핑·상점가
    STREET = "STREET"  # 거리·골목 풍경
    THEME_PARK = "THEME_PARK"  # 테마파크·놀이공원
    AQUARIUM_ZOO = "AQUARIUM_ZOO"  # 수족관·동물원
    # 기타
    ETC = "ETC"


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


# 사진 장소 검색 요청 (백엔드 PhotoPlaceSearchRequest의 상위집합)
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


# Cloud Vision 랜드마크 감지 원신호
class LandmarkDetection(BaseModel):
    name: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    score: float = Field(ge=0, le=1)  # Vision 신뢰도 (0~1)


# Google Places 로 확정한 실제 장소 정보 (좌표는 항상 여기서 나온다)
class ResolvedPlace(BaseModel):
    place_id: str
    name: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    formatted_address: str | None = None
    # 도시/국가: Places addressComponents 에서 구조화 파싱 (백엔드 계약 매핑용)
    city: str | None = None
    country: str | None = None
    rating: float | None = Field(default=None, ge=0, le=5)
    review_count: int | None = Field(default=None, ge=0)  # 평점 신뢰도 판단용 리뷰 수
    primary_type: str | None = None  # Google 장소 유형 (예: cafe) — 카테고리 역매핑용


# Gemini 비전 식별 원신호
class VisionIdentification(BaseModel):
    place_name_guess: str | None = None  # 추정 장소명 (없을 수 있음)
    category: PlaceCategory  # 추정 카테고리/분위기
    vibe_keywords: list[str] = Field(default_factory=list)
    reason: str  # 추정 근거
    confidence: float = Field(ge=0, le=1)  # LLM 자기 확신도 (0~1)


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
