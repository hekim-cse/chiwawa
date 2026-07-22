# 이미지 소스(URL/경로)를 바이트로 로딩 + 보안 검증
# - URL: SSRF 방지 (스킴 검증, 사설/루프백/링크로컬/메타데이터 IP 차단, 리다이렉트 금지)
# - 경로: 경로 탈출 방지 (허용 base 디렉토리 밖 접근 차단)
# 검증 로직(validate_*)은 순수 함수로 분리해 네트워크·파일 없이 테스트한다.
import ipaddress
import socket
from pathlib import Path
from urllib.parse import urlparse

import httpx

from ai.image_search.domain.search_schemas import ImageSearchRequest


# 이미지 로딩/검증 실패
class ImageLoadError(ValueError):
    pass


_ALLOWED_SCHEMES = {"http", "https"}


# URL 을 SSRF 관점에서 검증한다 (문제 없으면 반환값 없음, 위험하면 ImageLoadError).
# - http/https 만 허용
# - 호스트를 DNS 해석해, 해석된 모든 주소가 공인(global) IP 인지 확인
#   (루프백·사설·링크로컬·메타데이터·unspecified 는 차단)
def validate_image_url(url: str) -> None:
    parsed = urlparse(url)

    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise ImageLoadError(f"허용되지 않은 URL 스킴입니다: {parsed.scheme!r}")

    host = parsed.hostname
    if not host:
        raise ImageLoadError("URL 에 호스트가 없습니다.")

    for address in _resolve_addresses(host):
        if not address.is_global:
            raise ImageLoadError(
                f"내부/사설 주소로의 요청은 차단됩니다: {host} -> {address}"
            )


# 호스트명을 IP 주소 목록으로 해석 (해석 실패도 차단 대상)
def _resolve_addresses(host: str) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    # 호스트가 이미 IP 리터럴이면 그대로 사용
    try:
        return [ipaddress.ip_address(host)]
    except ValueError:
        pass

    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise ImageLoadError(f"호스트를 해석할 수 없습니다: {host}") from exc

    addresses: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    for info in infos:
        ip_str = info[4][0]
        addresses.append(ipaddress.ip_address(ip_str))
    if not addresses:
        raise ImageLoadError(f"호스트를 해석할 수 없습니다: {host}")
    return addresses


# HEIC(아이폰 기본 포맷) 컨테이너의 ftyp 브랜드들
_HEIC_BRANDS = {b"heic", b"heix", b"hevc", b"heim", b"heis", b"mif1", b"msf1"}


# 이미지 바이트의 매직 넘버로 MIME 타입을 추정한다.
# 식별기(Gemini)에 올바른 타입을 넘기기 위함이며, 알 수 없으면 image/jpeg 로 둔다.
def detect_image_mime_type(image_bytes: bytes) -> str:
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if image_bytes.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    if image_bytes[4:8] == b"ftyp" and image_bytes[8:12] in _HEIC_BRANDS:
        return "image/heic"
    return "image/jpeg"


# 경로가 허용 base 디렉토리 안에 있는지 검증하고, 정규화된 절대경로를 반환한다.
# 경로 탈출(../)·절대경로로 base 밖 접근을 차단한다.
def validate_image_path(path: str, base_dir: Path) -> Path:
    base = base_dir.resolve()
    candidate = (base / path).resolve()

    # candidate 가 base 하위인지 확인
    if base != candidate and base not in candidate.parents:
        raise ImageLoadError(f"허용된 디렉토리 밖의 경로입니다: {path}")
    return candidate


# 이미지 소스를 바이트로 로딩한다.
# image_path 사용 시 allowed_base_dir 를 반드시 지정해야 한다(신뢰 디렉토리 한정).
# recognizer 가 한 곳에서 로딩해 두 식별기에 같은 이미지를 넘긴다.
# transport: httpx 전송 계층 주입용 (테스트에서 MockTransport, 실제 사용 시 None)
def load_image_bytes(
    request: ImageSearchRequest,
    allowed_base_dir: Path | None = None,
    timeout_seconds: float = 10.0,
    transport: httpx.BaseTransport | None = None,
) -> bytes:
    if request.image_path:
        if allowed_base_dir is None:
            raise ImageLoadError(
                "image_path 로딩에는 allowed_base_dir 지정이 필요합니다(임의 파일 읽기 방지)."
            )
        resolved = validate_image_path(request.image_path, allowed_base_dir)
        return resolved.read_bytes()

    url = request.image_url
    # 클라이언트 호출 전에 SSRF 가드를 먼저 통과시킨다(내부/사설 주소 차단)
    validate_image_url(url)
    # 리다이렉트로 SSRF 우회를 막기 위해 follow_redirects=False
    # 네트워크·HTTP 오류는 ImageLoadError(ValueError 계열)로 감싸,
    # 호출자가 이미지 로딩 실패를 한 종류의 예외로 처리하게 한다
    try:
        with httpx.Client(
            timeout=timeout_seconds, follow_redirects=False, transport=transport
        ) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.content
    except httpx.HTTPError as exc:
        raise ImageLoadError(f"이미지 다운로드에 실패했습니다: {url} ({exc})") from exc
