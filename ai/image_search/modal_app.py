# Modal 환경에서 사진 → 장소 후보 검색(PlaceRecognizer)을 실행하는 HTTP entrypoint
from typing import Any

import modal
from pydantic import ValidationError

from ai.image_search.domain.search_schemas import ImageSearchRequest
from ai.image_search.providers.landmark_provider import LandmarkProvider
from ai.image_search.providers.places_provider import PlacesProvider
from ai.image_search.providers.vision_llm_provider import VisionLlmProvider
from ai.image_search.services.image_loader import ImageLoadError
from ai.image_search.services.place_recognizer import PlaceRecognizer


# Modal에 배포할 운영용 App
app = modal.App("chiwawa-image-search")


# Modal 컨테이너에서 사용할 Python 환경
# google-genai: Gemini 비전 추론 SDK (route_planner 에는 없는 image_search 전용 의존)
# Python 3.11 은 배포 런타임. 백엔드(in-process)는 3.13 이라 같은 코드가 두 런타임에서 돌므로
# CI(ai-image-search-ci.yml)가 3.11·3.13 양쪽에서 테스트해 문법/동작 스큐를 막는다.
# 공유 라이브러리는 백엔드 pyproject 의 하한과 맞춰 두 경로의 버전 편차를 줄이고,
# fastapi 는 상한을 둬 예상치 못한 파괴적 업그레이드를 막는다.
image = (
    modal.Image.debian_slim(
        python_version="3.11",
    )
    .pip_install(
        "httpx>=0.28.0",
        "python-dotenv",
        "pydantic>=2.11.0",
        "google-genai>=1.0.0",
        "fastapi>=0.115,<1",
    )
    # ai/ 트리 전체(route_planner·free_time 포함)를 올린다. image_search 는 ai.image_search 만
    # import 하지만 route_planner/modal_app.py 와 동일한 관례로 트리 전체를 싣는다(의도적).
    .add_local_python_source(
        "ai",
    )
)


# Modal Dashboard의 API Secret
# provider 3종은 생성자에 키를 넘기지 않으면 환경변수에서 읽으므로,
# 이 Secret 은 아래 세 이름을 '정확히' 그대로 정의해야 한다
# (하나라도 다르면 배포는 통과하고 첫 호출 때 ValueError 로만 드러난다):
#   GOOGLE_MAPS_API_KEY          (Places)
#   GOOGLE_CLOUD_VISION_API_KEY  (Landmark)
#   GEMINI_API_KEY               (Gemini 비전)
image_search_secret = modal.Secret.from_name(
    "chiwawa-image-search",
)


# payload를 검증하고 PlaceRecognizer를 실행해 JSON 응답으로 변환
# recognizer 를 주입받아 순수하게 유지 → 테스트에서 가짜 recognizer 로 경계를 검증한다.
def search_photo_payload(
    payload: dict[str, Any],
    recognizer: PlaceRecognizer,
) -> dict[str, Any]:
    request = (
        ImageSearchRequest
        .model_validate(payload)
    )

    result = recognizer.search(request)

    return result.model_dump(
        mode="json"
    )


# Modal HTTP Web Function
#
# 보안 주의: 현재 인증 미적용(공개 URL). 호출마다 Vision+Gemini+Places 유료 API 를 쓰므로
# 배포 전에 인증 방식(Modal proxy-auth 또는 공유 시크릿 헤더)을 결정·배선해야 한다.
# max_containers 로 비용 폭주 상한만 우선 걸어 둔 상태.
@app.function(
    image=image,
    secrets=[
        image_search_secret,
    ],
    timeout=120,
    # 비용 상한: 재시도 폭주·남용 시 유료 컨테이너가 무한 확장되지 않도록
    # 동시 컨테이너 수를 제한한다(cost DoS 방어).
    max_containers=10,
)
@modal.fastapi_endpoint(
    method="POST",
    # docs=False: 공개 URL 에 인터랙티브 Swagger 탐색기를 노출하지 않는다.
    docs=False,
)
def search_photo(
    payload: dict[str, Any],
) -> dict[str, Any]:
    # 실 IO provider 는 여기서 생성 (키는 Secret 이 주입한 환경변수에서 로드)
    recognizer = PlaceRecognizer(
        landmark=LandmarkProvider(),
        vision_llm=VisionLlmProvider(),
        places=PlacesProvider(),
    )

    try:
        return search_photo_payload(
            payload=payload,
            recognizer=recognizer,
        )
    except ImageLoadError as error:
        # 이미지 로딩·SSRF 차단 실패 → 입력 문제 (ValueError 하위라 먼저 잡는다)
        from fastapi import HTTPException

        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error
    except ValidationError as error:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=422,
            detail=error.errors(),
        ) from error
    except ValueError as error:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error
    except RuntimeError as error:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=502,
            detail=str(error),
        ) from error
