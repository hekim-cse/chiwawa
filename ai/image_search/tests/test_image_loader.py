# services/image_loader.py 의 SSRF 가드·경로 제한 검증 (순수 함수, 네트워크·파일 I/O 없음)
# 다운로드 경로는 httpx MockTransport 를 주입해 실제 네트워크 없이 검증한다.
import httpx
import pytest

from ai.image_search.domain.search_schemas import ImageSearchRequest
from ai.image_search.services.image_loader import (
    ImageLoadError,
    load_image_bytes,
    validate_image_path,
    validate_image_url,
)


class TestValidateImageUrl:
    # 정상 http/https URL(공인 IP로 해석)은 통과한다
    # 실제 DNS에 의존하지 않도록 getaddrinfo 를 공인 IP로 모킹한다
    def test_accepts_public_https_url(self, monkeypatch):
        monkeypatch.setattr(
            "ai.image_search.services.image_loader.socket.getaddrinfo",
            lambda *a, **k: [(2, 1, 6, "", ("93.184.216.34", 0))],
        )

        validate_image_url("https://example.com/photo.jpg")
        validate_image_url("http://images.example.org/a.png")

    # http/https 가 아닌 스킴은 거부한다 (file://, ftp://, gopher:// 등)
    @pytest.mark.parametrize(
        "url",
        [
            "file:///etc/passwd",
            "ftp://example.com/a.jpg",
            "gopher://example.com/",
            "data:image/png;base64,AAAA",
        ],
    )
    def test_rejects_non_http_scheme(self, url):
        with pytest.raises(ImageLoadError):
            validate_image_url(url)

    # 루프백/사설/링크로컬/메타데이터 IP 는 거부한다 (SSRF 차단)
    @pytest.mark.parametrize(
        "url",
        [
            "http://127.0.0.1/a.jpg",  # 루프백
            "http://localhost/a.jpg",  # 루프백 이름
            "http://10.0.0.5/a.jpg",  # 사설 A
            "http://172.16.3.4/a.jpg",  # 사설 B
            "http://192.168.1.10/a.jpg",  # 사설 C
            "http://169.254.169.254/latest/meta-data/",  # 클라우드 메타데이터
            "http://[::1]/a.jpg",  # IPv6 루프백
            "http://0.0.0.0/a.jpg",  # unspecified
        ],
    )
    def test_rejects_internal_addresses(self, url):
        with pytest.raises(ImageLoadError):
            validate_image_url(url)

    # 호스트가 없는 URL 도 거부한다
    def test_rejects_url_without_host(self):
        with pytest.raises(ImageLoadError):
            validate_image_url("http:///a.jpg")

    # 해석할 수 없는 호스트는 차단한다 (fail-closed)
    def test_rejects_unresolvable_host(self, monkeypatch):
        import socket as _socket

        def boom(*a, **k):
            raise _socket.gaierror("name resolution failed")

        monkeypatch.setattr(
            "ai.image_search.services.image_loader.socket.getaddrinfo", boom
        )
        with pytest.raises(ImageLoadError):
            validate_image_url("https://nonexistent.invalid/a.jpg")


class TestValidateImagePath:
    # 허용 base 디렉토리 안의 경로는 통과하고, 정규화된 경로를 돌려준다
    def test_accepts_path_inside_base(self, tmp_path):
        f = tmp_path / "photo.jpg"
        f.write_bytes(b"x")

        resolved = validate_image_path("photo.jpg", base_dir=tmp_path)

        assert resolved == f.resolve()

    # base 밖으로 탈출하는 경로(../)는 거부한다
    @pytest.mark.parametrize(
        "path",
        ["../secret.txt", "../../etc/passwd", "sub/../../escape.jpg"],
    )
    def test_rejects_traversal(self, tmp_path, path):
        with pytest.raises(ImageLoadError):
            validate_image_path(path, base_dir=tmp_path)

    # 절대 경로도 거부한다 (base 밖 임의 파일 접근 차단)
    def test_rejects_absolute_path(self, tmp_path):
        with pytest.raises(ImageLoadError):
            validate_image_path("/etc/passwd", base_dir=tmp_path)


class TestLoadImageBytes:
    # URL 다운로드: transport 주입으로 실제 네트워크 없이 바이트를 받아온다
    # (공인 IP 리터럴 호스트라 DNS 조회 없이 SSRF 가드를 통과한다)
    def test_downloads_url_via_injected_transport(self):
        captured = {}

        def handler(request):
            captured["url"] = str(request.url)
            return httpx.Response(200, content=b"\xff\xd8\xff-image-bytes")

        req = ImageSearchRequest(image_url="https://93.184.216.34/photo.jpg")

        result = load_image_bytes(req, transport=httpx.MockTransport(handler))

        assert result == b"\xff\xd8\xff-image-bytes"
        assert captured["url"] == "https://93.184.216.34/photo.jpg"

    # HTTP 오류 상태(4xx/5xx)는 예외로 전파한다 (조용히 삼키지 않음)
    def test_raises_on_http_error_status(self):
        def handler(request):
            return httpx.Response(404, content=b"not found")

        req = ImageSearchRequest(image_url="https://93.184.216.34/photo.jpg")

        with pytest.raises(httpx.HTTPStatusError):
            load_image_bytes(req, transport=httpx.MockTransport(handler))

    # 내부 주소로의 다운로드는 클라이언트 호출 전에 SSRF 가드가 먼저 막는다
    def test_download_blocks_internal_address_before_request(self):
        def handler(request):  # pragma: no cover - 호출되면 안 됨
            raise AssertionError("차단됐어야 하는데 요청이 나갔다")

        req = ImageSearchRequest(image_url="http://169.254.169.254/latest/meta-data/")

        with pytest.raises(ImageLoadError):
            load_image_bytes(req, transport=httpx.MockTransport(handler))

    # 로컬 경로: base 안의 파일을 바이트로 읽는다 (네트워크 없음)
    def test_reads_local_file_within_base(self, tmp_path):
        f = tmp_path / "photo.jpg"
        f.write_bytes(b"local-bytes")
        req = ImageSearchRequest(image_path="photo.jpg")

        result = load_image_bytes(req, allowed_base_dir=tmp_path)

        assert result == b"local-bytes"

    # image_path 인데 base 디렉토리 미지정 → 거부 (임의 파일 읽기 방지)
    def test_image_path_without_base_dir_is_rejected(self):
        req = ImageSearchRequest(image_path="photo.jpg")

        with pytest.raises(ImageLoadError):
            load_image_bytes(req)
