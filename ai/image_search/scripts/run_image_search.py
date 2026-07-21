# 사진 한 장으로 장소 식별과 근처 추천을 실행하는 CLI 스크립트
# 실사진 end-to-end 검증용: 캐스케이드 전체(랜드마크 → Gemini → Places)를 실제 API 로 실행한다.
# 사용 예 (레포 루트에서):
#   ai/.venv/bin/python -m ai.image_search.scripts.run_image_search --image-path 사진.jpg
#   ai/.venv/bin/python -m ai.image_search.scripts.run_image_search --image-path 사진.jpg --debug
from __future__ import annotations

import argparse
import json
from functools import partial
from pathlib import Path

from pydantic import ValidationError

from ai.image_search.domain.search_schemas import ImageSearchRequest
from ai.image_search.providers.landmark_provider import LandmarkProvider
from ai.image_search.providers.places_provider import PlacesProvider
from ai.image_search.providers.vision_llm_provider import VisionLlmProvider
from ai.image_search.services.image_loader import load_image_bytes
from ai.image_search.services.place_recognizer import PlaceRecognizer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "사진 한 장으로 장소를 식별하고 근처 장소를 추천합니다. "
            "API 키 3종(ai/image_search/.env)이 필요합니다."
        )
    )

    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--image-path",
        help="로컬 사진 파일 경로 (JPEG/PNG 권장, HEIC 은 JPEG 변환 후 사용)",
    )
    source.add_argument(
        "--image-url",
        help="호스팅 사진 URL (리다이렉트되는 URL 은 지원하지 않음)",
    )
    parser.add_argument("--note", help="사용자 메모 힌트 (예: 야경)")
    parser.add_argument(
        "--max-candidates",
        type=int,
        default=5,
        help="반환 후보 최대 개수 (식별 1 + 근처 추천, 기본 5)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="각 provider 를 직접 호출해 캐스케이드가 삼키는 원본 오류를 노출",
    )

    return parser.parse_args()


# CLI 인자를 ImageSearchRequest 로 변환 (로컬 경로는 절대경로로 정규화)
def build_request(
    image_path: str | None,
    image_url: str | None,
    note: str | None,
    max_candidates: int,
) -> ImageSearchRequest:
    resolved_path = str(Path(image_path).resolve()) if image_path else None
    return ImageSearchRequest(
        image_path=resolved_path,
        image_url=image_url,
        note=note,
        max_candidates=max_candidates,
    )


# provider 3종을 조립해 recognizer 를 만든다 (테스트에서 가짜 provider 주입)
# 로컬 사진은 그 파일이 있는 디렉토리만 허용 base 로 지정해 로딩한다
def build_recognizer(
    image_path: Path | None = None,
    landmark=None,
    vision_llm=None,
    places=None,
) -> PlaceRecognizer:
    image_loader = (
        partial(load_image_bytes, allowed_base_dir=image_path.resolve().parent)
        if image_path
        else None
    )
    return PlaceRecognizer(
        landmark=landmark or LandmarkProvider(),
        vision_llm=vision_llm or VisionLlmProvider(),
        places=places or PlacesProvider(),
        image_loader=image_loader,
    )


# 캐스케이드 전체 실행 (결과에 원신호 signals 포함 — 실검증 진단용)
def run_image_search(request: ImageSearchRequest, recognizer: PlaceRecognizer) -> dict:
    return recognizer.search(request).model_dump(mode="json")


# 각 provider 를 캐스케이드 밖에서 직접 호출하는 진단 모드
# (_safe_* 가 삼키는 API 키·권한·쿼터 오류를 원문 그대로 노출한다)
def run_debug(
    request: ImageSearchRequest,
    image_path: Path | None = None,
    landmark=None,
    vision_llm=None,
    places=None,
) -> dict:
    landmark = landmark or LandmarkProvider()
    vision_llm = vision_llm or VisionLlmProvider()
    places = places or PlacesProvider()

    loader = (
        partial(load_image_bytes, allowed_base_dir=image_path.resolve().parent)
        if image_path
        else load_image_bytes
    )
    image_bytes = loader(request)

    report: dict = {"image_bytes": len(image_bytes)}

    landmark_result = _probe(
        report, "landmark", lambda: landmark.detect(image_bytes=image_bytes)
    )
    llm_result = _probe(
        report,
        "vision_llm",
        lambda: vision_llm.identify(image_bytes=image_bytes, note=request.note),
    )

    # 식별된 장소명이 있으면 좌표 확정(Places)까지 진단
    seed_name = None
    if landmark_result is not None:
        seed_name = landmark_result.name
    elif llm_result is not None and llm_result.place_name_guess:
        seed_name = llm_result.place_name_guess

    if seed_name:
        _probe(report, "places_resolve", lambda: places.resolve_place(seed_name))
    else:
        report["places_resolve"] = {"skipped": "식별된 장소명이 없습니다."}

    return report


# 호출 하나를 실행해 성공 결과 또는 오류 원문을 report 에 기록
def _probe(report: dict, key: str, call):
    try:
        result = call()
    except Exception as error:  # noqa: BLE001 - 진단 모드는 모든 오류를 보고한다
        report[key] = {"ok": False, "error": f"{type(error).__name__}: {error}"}
        return None
    report[key] = {
        "ok": True,
        "result": result.model_dump(mode="json") if result is not None else None,
    }
    return result


# CLI 실행 진입점
def main() -> int:
    args = parse_args()

    try:
        request = build_request(
            image_path=args.image_path,
            image_url=args.image_url,
            note=args.note,
            max_candidates=args.max_candidates,
        )
        photo = Path(args.image_path) if args.image_path else None

        if args.debug:
            payload = run_debug(request, image_path=photo)
        else:
            recognizer = build_recognizer(image_path=photo)
            payload = run_image_search(request, recognizer)
    except ValidationError as error:
        print("[이미지 장소 검색 실패]")
        print("요청 값이 ImageSearchRequest 구조와 맞지 않습니다.")
        print(error)
        return 1
    except (RuntimeError, ValueError, OSError) as error:
        print("[이미지 장소 검색 실패]")
        print(error)
        return 1

    print("[이미지 장소 검색 성공]")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
