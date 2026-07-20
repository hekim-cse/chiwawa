# 사진 → 장소 후보를 만드는 전체 UseCase를 조합하는 Application Service
# 세 provider(랜드마크·Gemini·Places)를 캐스케이드로 엮는다.
# 원칙: 사진 이해는 AI가, 좌표·사실은 항상 Google Places 실제값으로.
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from ai.image_search.domain.schemas import (
    LandmarkDetection,
    PlaceCategory,
    ResolvedPlace,
    VisionIdentification,
)
from ai.image_search.domain.search_schemas import (
    CandidateSource,
    ImageSearchRequest,
    ImageSearchResult,
    PlaceCandidate,
    RecognitionSignals,
    RecognitionStatus,
)
from ai.image_search.services.image_loader import load_image_bytes


# --- provider 인터페이스 (구체 구현에 직접 의존하지 않도록 Protocol 로 주입) ---
class LandmarkDetector(Protocol):
    def detect(
        self, image_bytes: bytes | None = None, image_url: str | None = None
    ) -> LandmarkDetection | None: ...


class VisionIdentifier(Protocol):
    def identify(
        self, image_bytes: bytes, mime_type: str = "image/jpeg", note: str | None = None
    ) -> VisionIdentification: ...


class PlacesResolver(Protocol):
    def resolve_place(
        self, place_name: str, language_code: str = "ko", region_code: str = "JP"
    ) -> ResolvedPlace: ...

    def search_nearby(
        self,
        latitude: float,
        longitude: float,
        category: PlaceCategory | None = None,
        radius_m: float = 1500,
        max_result_count: int = 5,
        language_code: str = "ko",
        region_code: str = "JP",
    ) -> list[ResolvedPlace]: ...


# 캐스케이드 동작 설정 (step 7 실호출 검증 후 튜닝 가능)
@dataclass(frozen=True)
class PlaceRecognizerConfig:
    landmark_score_threshold: float = 0.6  # 이 값 이상이면 랜드마크 채택, 미만이면 LLM 폴백
    nearby_radius_m: float = 1500  # 근처 검색 반경
    nearby_confidence_decay: float = 0.15  # 근처 후보 confidence 순차 감소폭


class PlaceRecognizer:
    # provider 3종을 Protocol 로 주입 (테스트에서 가짜 provider, 실제 사용 시 구체 provider)
    # image_loader: 이미지 로딩 함수 주입용 (테스트에서 가짜, 실제 사용 시 load_image_bytes)
    def __init__(
        self,
        landmark: LandmarkDetector,
        vision_llm: VisionIdentifier,
        places: PlacesResolver,
        config: PlaceRecognizerConfig | None = None,
        image_loader: Callable[[ImageSearchRequest], bytes] | None = None,
    ) -> None:
        self.landmark = landmark
        self.vision_llm = vision_llm
        self.places = places
        self.config = config or PlaceRecognizerConfig()
        self._load = image_loader or load_image_bytes

    # 사진 요청을 받아 식별 + 근처 추천 결과를 만든다
    def search(self, request: ImageSearchRequest) -> ImageSearchResult:
        image_bytes = self._load(request)

        # 두 식별기 실행 (각각 우아하게 저하 — 하나 실패해도 다른 하나로 진행)
        landmark = self._safe_detect(image_bytes)
        llm = self._safe_identify(image_bytes, request.note)
        signals = RecognitionSignals(landmark=landmark, llm=llm)

        # 캐스케이드: 자신 있는 랜드마크 우선, 아니면 LLM 추정
        seed = self._pick_seed(landmark, llm)
        if seed is None:
            return self._failed(signals)
        seed_name, base_conf, source, reason = seed

        # 카테고리는 LLM 이 제공 (근처 추천 필터에 사용) — LLM 없으면 미지정
        category = llm.category if llm is not None else None

        # 좌표는 항상 Places 로 재확정 (랜드마크가 준 좌표도 신뢰하지 않음, 환각 차단)
        resolved = self._safe_resolve(seed_name)
        if resolved is None:
            return self._failed(signals)

        identified = self._to_candidate(resolved, base_conf, reason, source, category, request)

        # 근처 추천 (식별 1건 제외한 나머지 개수만큼)
        nearby_wanted = max(0, request.max_candidates - 1)
        nearby_candidates = self._build_nearby(
            resolved, category, nearby_wanted, base_conf, request
        )

        candidates = [identified, *nearby_candidates]
        status = (
            RecognitionStatus.SUCCESS if nearby_candidates else RecognitionStatus.PARTIAL
        )
        return ImageSearchResult(
            identified=identified,
            candidates=candidates,
            status=status,
            signals=signals,
        )

    # 캐스케이드 판단: (seed_name, confidence, source, reason) 또는 None
    def _pick_seed(
        self, landmark: LandmarkDetection | None, llm: VisionIdentification | None
    ) -> tuple[str, float, CandidateSource, str] | None:
        if landmark is not None and landmark.score >= self.config.landmark_score_threshold:
            reason = f"랜드마크 감지 결과와 일치 (신뢰도 {landmark.score:.2f})"
            return landmark.name, landmark.score, CandidateSource.LANDMARK, reason
        if llm is not None and llm.place_name_guess:
            return llm.place_name_guess, llm.confidence, CandidateSource.LLM, llm.reason
        return None

    # 근처 후보 리스트 생성 (confidence 순차 감소)
    def _build_nearby(
        self,
        resolved: ResolvedPlace,
        category: PlaceCategory | None,
        wanted: int,
        base_conf: float,
        request: ImageSearchRequest,
    ) -> list[PlaceCandidate]:
        if wanted <= 0:
            return []
        nearby_places = self._safe_nearby(resolved, category, wanted)
        return [
            self._to_candidate(
                place,
                self._decay(base_conf, index),
                "근처의 비슷한 장소",
                CandidateSource.NEARBY,
                category,
                request,
            )
            for index, place in enumerate(nearby_places)
        ]

    # ResolvedPlace → PlaceCandidate 매핑 (도시/국가는 Places → 요청 힌트 순으로 채움)
    @staticmethod
    def _to_candidate(
        place: ResolvedPlace,
        confidence: float,
        reason: str,
        source: CandidateSource,
        category: PlaceCategory | None,
        request: ImageSearchRequest,
    ) -> PlaceCandidate:
        return PlaceCandidate(
            name=place.name,
            city=place.city or request.city or "",
            country=place.country or request.country or "",
            latitude=place.latitude,
            longitude=place.longitude,
            confidence=confidence,
            reason=reason,
            category=category or PlaceCategory.ETC,
            source=source,
            place_id=place.place_id,
            rating=place.rating,
        )

    # 근처 후보 confidence 를 순위 기반으로 감소 (0.1 하한)
    def _decay(self, base_conf: float, index: int) -> float:
        value = base_conf - self.config.nearby_confidence_decay * (index + 1)
        return round(max(0.1, value), 2)

    # 식별 실패 시 결과 (원신호는 보존)
    @staticmethod
    def _failed(signals: RecognitionSignals) -> ImageSearchResult:
        return ImageSearchResult(
            identified=None,
            candidates=[],
            status=RecognitionStatus.FAILED,
            signals=signals,
        )

    # --- 각 외부 호출을 우아하게 저하 (예외 → None/빈 리스트) ---
    def _safe_detect(self, image_bytes: bytes) -> LandmarkDetection | None:
        try:
            return self.landmark.detect(image_bytes=image_bytes)
        except Exception:
            return None

    def _safe_identify(
        self, image_bytes: bytes, note: str | None
    ) -> VisionIdentification | None:
        try:
            return self.vision_llm.identify(image_bytes=image_bytes, note=note)
        except Exception:
            return None

    def _safe_resolve(self, place_name: str) -> ResolvedPlace | None:
        try:
            return self.places.resolve_place(place_name)
        except Exception:
            return None

    def _safe_nearby(
        self, resolved: ResolvedPlace, category: PlaceCategory | None, wanted: int
    ) -> list[ResolvedPlace]:
        try:
            return self.places.search_nearby(
                latitude=resolved.latitude,
                longitude=resolved.longitude,
                category=category,
                radius_m=self.config.nearby_radius_m,
                max_result_count=wanted,
            )
        except Exception:
            return []
