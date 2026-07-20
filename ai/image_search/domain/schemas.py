# 데이터 구조 정의 파일 (내부/provider 모델 + 공용 어휘)
# - provider 원신호: LandmarkDetection(Vision) · VisionIdentification(Gemini) · ResolvedPlace(Places)
# - 공용 어휘: PlaceCategory (내부·계약 양쪽에서 사용)
# 백엔드와 주고받는 계약 DTO 는 domain/search_schemas.py 에 있다.
from enum import Enum

from pydantic import BaseModel, Field


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


# Cloud Vision 랜드마크 감지 원신호
class LandmarkDetection(BaseModel):
    name: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    score: float = Field(ge=0, le=1)  # Vision 신뢰도 (0~1)


# Gemini 비전 식별 원신호
class VisionIdentification(BaseModel):
    place_name_guess: str | None = None  # 추정 장소명 (없을 수 있음)
    category: PlaceCategory  # 추정 카테고리/분위기
    vibe_keywords: list[str] = Field(default_factory=list)
    reason: str  # 추정 근거
    confidence: float = Field(ge=0, le=1)  # LLM 자기 확신도 (0~1)
    visible_text: list[str] = Field(default_factory=list)  # 사진 속 간판/글자 (장소 특정 단서)


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
