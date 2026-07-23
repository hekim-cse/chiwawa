# 이미지 장소 검색 Modal 연동 백엔드 작업 결과

## 참고 문서

- `/Users/jmllem/Desktop/연동요청서 3차 .md`
- 대상 Modal 함수: `chiwawa-image-search`의 `POST search_photo`

## 결론

백엔드 작업이 필요하며, 현재 구현했다. Modal URL이 설정된 경우에만 HTTP 방식으로 전환하고, URL이 비어 있으면 기존 프로세스 내부 이미지 검색을 계속 사용한다. 따라서 Modal 배포 전에도 백엔드가 바로 기동되며, 운영 전환 시 환경변수만 추가하면 된다.

이번 작업에서는 백엔드 파일만 변경했다. `ai/`, `frontend/`, 루트 Dockerfile, Git 커밋은 변경하지 않았다.

## 구현 내용

- `config.py`
  - `IMAGE_SEARCH_URL` 추가
  - `IMAGE_SEARCH_TIMEOUT_SECONDS` 기본값 `125`
  - `IMAGE_SEARCH_MAX_RETRIES` 기본값 `1`
- `services/image_search_client.py`
  - `httpx.AsyncClient`로 Modal endpoint 호출
  - 요청 JSON에 `image_url`, `image_path`, `note`, `latitude`, `longitude`, `city`, `country`, `max_candidates` 전달
  - Modal `ImageSearchResult` 응답 검증
  - `400/422`를 백엔드 `422`로 변환
  - 네트워크 오류와 `500/502/503/504`를 1회 재시도
  - 최종 upstream 오류를 백엔드 `502 Bad Gateway`로 변환
- `dependencies.py`
  - `IMAGE_SEARCH_URL`이 유효하면 원격 recognizer 선택
  - 미설정 또는 공백이면 기존 in-process recognizer 선택
- `services/photo_places.py`, `routers/photo_places.py`
  - 원격 async 호출을 지원
  - 기존 동기 recognizer는 threadpool에서 실행해 fallback 호환성 유지
- `errors.py`, `main.py`
  - upstream 오류 타입과 502 예외 처리 추가
- `.env.example`
  - 신규 환경변수 예시 추가

## 서버 설정

Modal 함수 배포 후 발급된 실제 URL을 백엔드 서버의 `.env`에 입력한다.

```dotenv
IMAGE_SEARCH_URL=https://<modal-app-url>/search_photo
IMAGE_SEARCH_TIMEOUT_SECONDS=125
IMAGE_SEARCH_MAX_RETRIES=1
```

`IMAGE_SEARCH_URL`을 비워 두면 원격 호출이 활성화되지 않는다. 기존 fallback을 사용하려면 현재처럼 Vision/Gemini 관련 환경변수를 유지해야 한다.

## 현재 계약의 제한

현재 백엔드 `POST /trips/{trip_id}/photo-search` 요청은 `image_url`을 받는다. 이번 백엔드 작업은 이 URL을 Modal에 전달하는 범위로 맞췄으며, 프론트엔드의 로컬 파일 업로드 UI나 업로드 스토리지는 변경하지 않았다.

따라서 Modal이 이미지를 내려받으려면 `image_url`이 Modal 서버에서 접근 가능한 URL이어야 한다. 백엔드 컨테이너 내부의 로컬 파일 경로를 전달하는 방식은 원격 Modal에서 사용할 수 없다.

## 배포 전 확인 사항

1. Modal 앱을 실제로 배포하고 `/search_photo` URL이 응답하는지 확인한다.
2. Modal endpoint가 현재 공개 인증 방식이라면 데모 이후에는 별도 shared secret 또는 인증을 추가한다.
3. Modal에서 접근 가능한 이미지 URL로 백엔드의 photo-search API를 호출해 200 응답과 후보 매핑을 확인한다.
4. Modal 장애·타임아웃 시 백엔드가 502를 반환하는지 확인한다.
5. 원격 경로 검증 후에만 기존 `ai` 코드, 관련 Docker 의존성, Vision/Gemini 키 제거를 별도 작업으로 진행한다.

## 검증 결과

- 신규 원격 client 테스트: `4 passed`
- 백엔드 전체 테스트: `90 passed`
- 변경 파일 대상 Ruff lint: 통과
- 백엔드 BasedPyright: `0 errors, 0 warnings, 0 notes`
