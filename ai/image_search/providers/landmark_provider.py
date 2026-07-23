# Google Cloud Vision API(REST)를 호출해 사진 속 "랜드마크"를 감지하는 Provider
# 캐스케이드의 1차 식별기: 유명 명소에 강하고 저렴하다.
import base64

import httpx

from ai.image_search.domain.schemas import LandmarkDetection
from ai.image_search.providers.env import get_google_cloud_vision_api_key
from ai.image_search.providers.errors import (
    InvalidProviderResponseError,
    ProviderHttpError,
    ProviderTimeoutError,
    ProviderTransportError,
)


# Cloud Vision 랜드마크 감지를 감싸 사진 -> LandmarkDetection 으로 변환하는 Provider
class LandmarkProvider:
    ANNOTATE_URL = "https://vision.googleapis.com/v1/images:annotate"

    # api_key: Cloud Vision API 키 (없으면 환경변수에서 가져옴)
    # max_results: 감지 후보 최대 개수 (좌표 없는 후보를 건너뛸 여지를 두기 위해 1보다 크게)
    # timeout_seconds: API 호출 타임아웃 (초)
    # transport: httpx 전송 계층 주입용 (테스트에서 MockTransport, 실제 사용 시 None)
    def __init__(
        self,
        api_key: str | None = None,
        max_results: int = 3,
        timeout_seconds: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.api_key = api_key or get_google_cloud_vision_api_key()
        self.max_results = max_results
        self.timeout_seconds = timeout_seconds
        self._transport = transport

    # 내부 httpx 클라이언트 생성 (주입된 transport 가 있으면 그것을 사용)
    def _client(self) -> httpx.Client:
        return httpx.Client(timeout=self.timeout_seconds, transport=self._transport)

    # 사진에서 랜드마크를 감지한다.
    # 입력: image_bytes(로컬 파일 내용) 또는 image_url(호스팅 이미지) 중 하나 필수
    # 반환: 가장 신뢰도 높은 유효(좌표 보유) 랜드마크 / 감지 없으면 None
    #   - "랜드마크 아님"은 정상 상황이며(카페·골목 등) 캐스케이드가 LLM 으로 폴백할 근거다
    # 예외: 시간초과 → ProviderTimeoutError, 전송실패 → ProviderTransportError,
    #       HTTP 오류 → ProviderHttpError, 응답 내 error → InvalidProviderResponseError
    #       (모두 RuntimeError 하위라 modal_app 은 502, recognizer 는 우아한 저하)
    def detect(
        self,
        image_bytes: bytes | None = None,
        image_url: str | None = None,
    ) -> LandmarkDetection | None:
        image_payload = self._build_image_payload(image_bytes, image_url)

        payload = {
            "requests": [
                {
                    "image": image_payload,
                    "features": [
                        {
                            "type": "LANDMARK_DETECTION",
                            "maxResults": self.max_results,
                        }
                    ],
                }
            ]
        }

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
        }

        try:
            with self._client() as client:
                response = client.post(self.ANNOTATE_URL, headers=headers, json=payload)
        except httpx.TimeoutException as error:
            raise ProviderTimeoutError(
                "Cloud Vision 요청이 시간 제한을 초과했습니다."
            ) from error
        except httpx.TransportError as error:
            raise ProviderTransportError(
                f"Cloud Vision 전송에 실패했습니다: {error}"
            ) from error

        # API 요청 실패 시 상태 코드를 명시적 타입으로 알린다
        if response.status_code >= 400:
            raise ProviderHttpError("Cloud Vision", response.status_code)

        return self._parse_response(response.json())

    # 이미지 입력을 Vision 요청 형식으로 변환 (bytes 는 base64, URL 은 imageUri)
    @staticmethod
    def _build_image_payload(
        image_bytes: bytes | None,
        image_url: str | None,
    ) -> dict:
        if image_bytes is not None:
            return {"content": base64.b64encode(image_bytes).decode("ascii")}
        if image_url is not None:
            return {"source": {"imageUri": image_url}}
        raise ValueError("image_bytes 또는 image_url 중 하나는 반드시 필요합니다.")

    # Vision 응답에서 가장 신뢰도 높은 유효 랜드마크를 추출
    # 주의: Vision 은 HTTP 200 안에 개별 error 객체를 심어 보낼 수 있다
    def _parse_response(self, data: dict) -> LandmarkDetection | None:
        responses = data.get("responses", [])
        if not responses:
            return None

        entry = responses[0]

        error = entry.get("error")
        if error:
            raise InvalidProviderResponseError(f"Cloud Vision API 오류 응답: {error}")

        for annotation in entry.get("landmarkAnnotations", []):
            detection = self._parse_annotation(annotation)
            if detection is not None:
                return detection

        return None

    # annotation 하나를 LandmarkDetection 으로 변환
    # 이름·score·좌표 중 하나라도 없으면 None (건너뛰고 다음 후보 확인)
    #   - 좌표는 이후 Places 로 재확정하지만, 스키마 계약상 감지 시점 좌표도 필수로 둔다
    @staticmethod
    def _parse_annotation(annotation: dict) -> LandmarkDetection | None:
        name = annotation.get("description")
        score = annotation.get("score")

        locations = annotation.get("locations", [])
        lat_lng = locations[0].get("latLng", {}) if locations else {}
        latitude = lat_lng.get("latitude")
        longitude = lat_lng.get("longitude")

        if not name or score is None or latitude is None or longitude is None:
            return None

        return LandmarkDetection(
            name=name,
            latitude=latitude,
            longitude=longitude,
            score=score,
        )
