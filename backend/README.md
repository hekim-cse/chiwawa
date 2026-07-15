# Chiwawa Backend

일본 자유여행 일정 추천·관리용 FastAPI 백엔드입니다. 이 디렉터리만으로 실행,
검증, wheel 빌드가 가능하며 프론트엔드나 AI 서비스 코드는 포함하지 않습니다.

## 저장 구조

- 운영(`APP_ENV=production`)의 여행 상태, OAuth state, 사용자, 사진 메타데이터는
  하나의 SQLite 파일에 저장됩니다. 요청별 `BEGIN IMMEDIATE` 트랜잭션으로 단일
  호스트의 여러 Uvicorn worker가 같은 상태를 공유합니다.
- Memorial 사진 원본은 `MEMORIAL_PHOTO_DIR` 아래 로컬 파일로만 저장합니다.
  디렉터리는 `0700`, 파일은 `0600`이며 DB에는 사용자별 상대 경로만 기록합니다.
- `MEMORIAL_PHOTO_DIR`는 사진 전용 디렉터리여야 하며 DB나 다른 애플리케이션
  파일을 포함할 수 없습니다. startup recovery가 이 경계 안의 사진만 관리합니다.
- S3나 다른 object storage는 사용하지 않습니다. 현재 구조는 로컬 SQLite와 사진
  디렉터리를 함께 마운트한 단일 호스트 배포만 지원합니다.
- 개발 모드는 빠른 로컬 작업을 위해 여행 상태를 프로세스 메모리에 둡니다.
  재시작·다중 worker 지속성을 검증하려면 운영 모드를 사용해야 합니다.

SQLite 마이그레이션의 단일 원본은 `src/chiwawa_backend/sql/*.sql`이며 wheel에도
포함됩니다. WAL, foreign key, busy timeout, migration version을 연결 시 확인합니다.

## 개발 실행

```bash
cp .env.example .env
uv sync --frozen
uv run uvicorn chiwawa_backend.main:app --reload --no-access-log --host 127.0.0.1 --port 8000
```

개발 모드에서는 여행 API가 호환용 actor `0`으로 동작합니다. `/api/v1/auth/me`와
회원 Memorial API는 개발 모드에서도 유효한 Bearer JWT가 필요합니다.

## 운영 실행

운영에서는 최소 다음 값을 명시해야 합니다.

```dotenv
APP_ENV=production
DATABASE_PATH=/var/lib/chiwawa/chiwawa.db
MEMORIAL_PHOTO_DIR=/var/lib/chiwawa/memorial_photos
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=https://api.example.com/api/v1/auth/google/callback
GOOGLE_OAUTH_COOKIE_SECURE=true
JWT_SECRET=replace-with-at-least-32-random-characters
```

`DATABASE_PATH`와 `MEMORIAL_PHOTO_DIR`는 운영에서 반드시 서로 겹치지 않는 절대
경로여야 합니다. 사진 경로는 비어 있거나 Chiwawa 사진 구조만 가진 전용
디렉터리를 지정하십시오. 두 경로 모두 같은 호스트의 영속 디스크에 두고 DB와
사진 디렉터리를 함께 백업하십시오. NFS 공유, 다중 호스트, S3를 전제로 한
구조가 아닙니다.

```bash
uv sync --frozen --no-dev
uv run uvicorn chiwawa_backend.main:app --workers 2 --no-access-log --host 0.0.0.0 --port 8000
```

운영 모드에서는 readiness가 OAuth/JWT/경로 설정을 검증하고, 모든 여행 API에
Bearer 인증과 사용자 소유권을 적용합니다. 다른 사용자의 여행 ID 접근은 존재
여부가 노출되지 않도록 404로 처리합니다. 설정이 불완전하면 liveness는 유지하되
`/ready`가 503을 반환하므로 트래픽을 보내면 안 됩니다.

## 상태와 문서

| 경로 | 용도 |
| --- | --- |
| `/health` | 프로세스 liveness |
| `/ready` | 설정, DB 마이그레이션·접속, 사진 경로·여유 공간 readiness |
| `/docs` | Swagger UI |
| `/redoc` | ReDoc |
| `/openapi.json` | OpenAPI JSON |

`/ready`의 의존성 검사 실패는 503입니다. 업로드 제한은 413, rate/concurrency는
429(`Retry-After` 포함), 로컬 디스크 watermark 부족은 507로 응답합니다. 공통
오류 본문은 `{"detail": "..."}`입니다.

## 품질 검사

```bash
make check
uv lock --check
uv build --wheel
```

`make check`는 Ruff format/lint, basedpyright, pytest를 실행합니다.

## 주요 계약

- 여행 기간은 최대 31일이며 일정 시각은 offset 없는 일본 현지 시각입니다.
- PATCH는 생략과 명시적 `null`을 구분합니다. nullable 필드는 `null`로 지울 수
  있고 required 필드의 `null`은 422입니다.
- 일정의 장소 참조는 같은 여행에 속해야 합니다. 참조된 장소 삭제 시 일정과
  계획의 선택적 참조를 `null`로 정리합니다.
- 사진 시각은 입력 offset과 관계없이 UTC instant로 정렬하고 `Asia/Tokyo` 현지
  날짜로 캘린더·타임라인에 배치합니다.
- 사진 업로드는 실제 파일 형식, 모든 애니메이션 프레임, 크기·픽셀·사용자 quota,
  rate·concurrency, 로컬 디스크 여유 공간을 검증합니다.

전체 경로는 [`docs/api/reference.md`](./docs/api/reference.md), 인증은
[`docs/api/auth.md`](./docs/api/auth.md), 로컬 사진 저장은
[`docs/api/memorial.md`](./docs/api/memorial.md), 구조는
[`docs/architecture/backend.md`](./docs/architecture/backend.md)를 확인하십시오.
