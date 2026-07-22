# services/image_loader.py 의 SSRF 가드·경로 제한 검증 (순수 함수, 네트워크·파일 I/O 없음)
# 다운로드 경로는 httpx MockTransport 를 주입해 실제 네트워크 없이 검증한다.
import httpx
import pytest

from ai.image_search.domain.search_schemas import ImageSearchRequest
from ai.image_search.services.image_loader import (
    ImageLoadError,
    detect_image_mime_type,
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

    # 이름 호스트(localhost)도 거부한다 — 실제 DNS 대신 getaddrinfo 를 모킹
    def test_rejects_localhost_name(self, monkeypatch):
        monkeypatch.setattr(
            "ai.image_search.services.image_loader.socket.getaddrinfo",
            lambda *a, **k: [(2, 1, 6, "", ("127.0.0.1", 0))],
        )
        with pytest.raises(ImageLoadError):
            validate_image_url("http://localhost/a.jpg")

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


class TestDetectImageMimeType:
    # 매직 바이트로 대표 이미지 포맷을 식별한다
    @pytest.mark.parametrize(
        "data,expected",
        [
            (b"\xff\xd8\xff\xe0\x00\x10JFIF", "image/jpeg"),
            (b"\x89PNG\r\n\x1a\n\x00\x00\x00", "image/png"),
            (b"GIF89a\x01\x00\x01\x00", "image/gif"),
            (b"GIF87a\x01\x00\x01\x00", "image/gif"),
            (b"RIFF\x24\x00\x00\x00WEBPVP8 ", "image/webp"),
            (b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00", "image/heic"),
        ],
    )
    def test_detects_known_formats(self, data, expected):
        assert detect_image_mime_type(data) == expected

    # 형식을 알 수 없으면 기본값(jpeg)으로 둔다
    def test_unknown_defaults_to_jpeg(self):
        assert detect_image_mime_type(b"not-an-image-header") == "image/jpeg"

    # 매우 짧은 바이트에도 예외 없이 기본값을 돌려준다
    def test_short_bytes_do_not_raise(self):
        assert detect_image_mime_type(b"") == "image/jpeg"
        assert detect_image_mime_type(b"\xff") == "image/jpeg"


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

    # HTTP 오류 상태(4xx/5xx)는 ImageLoadError 로 감싸 알린다
    # (호출자는 ValueError 계열 하나로 이미지 로딩 실패를 처리할 수 있어야 함)
    def test_wraps_http_error_status_as_image_load_error(self):
        def handler(request):
            return httpx.Response(404, content=b"not found")

        req = ImageSearchRequest(image_url="https://93.184.216.34/photo.jpg")

        with pytest.raises(ImageLoadError):
            load_image_bytes(req, transport=httpx.MockTransport(handler))

    # 연결 실패 등 네트워크 예외도 ImageLoadError 로 감싼다
    def test_wraps_network_error_as_image_load_error(self):
        def handler(request):
            raise httpx.ConnectError("connection refused")

        req = ImageSearchRequest(image_url="https://93.184.216.34/photo.jpg")

        with pytest.raises(ImageLoadError):
            load_image_bytes(req, transport=httpx.MockTransport(handler))

    # 상한 이하 다운로드는 정상 반환한다 (스트리밍 경로 검증)
    def test_download_within_cap_succeeds(self):
        def handler(request):
            return httpx.Response(200, content=b"\xff\xd8\xff" + b"a" * 500)

        req = ImageSearchRequest(image_url="https://93.184.216.34/photo.jpg")

        data = load_image_bytes(
            req, transport=httpx.MockTransport(handler), max_bytes=1024
        )
        assert data == b"\xff\xd8\xff" + b"a" * 500

    # 누적 크기가 상한을 넘으면 거부한다 (헤더 없이도 방어)
    def test_rejects_oversized_download(self):
        def handler(request):
            return httpx.Response(200, content=b"x" * 2048)

        req = ImageSearchRequest(image_url="https://93.184.216.34/photo.jpg")

        with pytest.raises(ImageLoadError):
            load_image_bytes(
                req, transport=httpx.MockTransport(handler), max_bytes=1024
            )

    # Content-Length 헤더가 상한을 넘으면 받기 전에 거부한다
    def test_rejects_by_content_length_header(self):
        body = b"x" * 100

        def handler(request):
            return httpx.Response(
                200, content=body, headers={"Content-Length": "9999999"}
            )

        req = ImageSearchRequest(image_url="https://93.184.216.34/photo.jpg")

        with pytest.raises(ImageLoadError):
            load_image_bytes(
                req, transport=httpx.MockTransport(handler), max_bytes=1024
            )

    # 전체 데드라인을 넘기면 거부한다 (느린 전송 차단 — monotonic 모킹)
    def test_rejects_when_deadline_exceeded(self, monkeypatch):
        clock = iter([0.0, 1000.0, 1000.0])
        monkeypatch.setattr(
            "ai.image_search.services.image_loader.time.monotonic",
            lambda: next(clock),
        )

        def handler(request):
            return httpx.Response(200, content=b"abc")

        req = ImageSearchRequest(image_url="https://93.184.216.34/photo.jpg")

        with pytest.raises(ImageLoadError):
            load_image_bytes(
                req,
                transport=httpx.MockTransport(handler),
                deadline_seconds=10.0,
            )

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
