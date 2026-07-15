# 백엔드 구조

## 배포 경계

현재 운영 구조는 **단일 호스트·다중 Uvicorn worker**를 대상으로 합니다.
SQLite DB와 Memorial 사진 디렉터리를 같은 호스트의 영속 디스크에 두며 S3나
공유 object storage는 사용하지 않습니다. 다중 호스트나 NFS가 필요해지면
정규화된 외부 DB와 별도 파일 저장 adapter로 교체해야 합니다.

개발 모드는 빠른 테스트를 위해 여행 aggregate를 메모리에 유지합니다. 운영
모드는 요청마다 SQLite snapshot을 읽고 쓰므로 worker와 재시작 사이에 상태가
유지됩니다.

## 모듈 구조

| 영역 | 경로 | 책임 |
| --- | --- | --- |
| 앱 조립 | `src/chiwawa_backend/main.py` | 설정 검증, middleware, DI, router, lifespan |
| 설정 | `src/chiwawa_backend/config.py` | 타입 환경 변수와 운영 readiness 검증 |
| HTTP | `routers/`, `exception_handlers.py` | 경로·응답 모델·공통 오류 매핑 |
| 계약 | `schemas/` | frozen, extra-forbid Pydantic v2 DTO |
| 도메인 | `services/` | 여행·장소·일정·인증·사진 규칙 |
| 여행 상태 | `state.py`, `services/state_store.py` | AppState snapshot과 SQLite 트랜잭션 |
| 로컬 사진 | `services/local_photo_*.py` | 경로 격리, 권한, staging delete, 복구 |
| 마이그레이션 | `src/chiwawa_backend/sql/*.sql` | wheel에 포함되는 유일한 schema 원본 |

## 요청 흐름

```text
HTTP request
  -> security headers
  -> upload JWT pre-auth + SQLite request concurrency slot
  -> Content-Length/chunked body limit
  -> FastAPI request validation
  -> Bearer actor + trip ownership
  -> request-scoped AppState transaction or member-photo repository
  -> response model / centralized error mapping
```

업로드 pre-auth와 요청 슬롯은 인증 실패 또는 여러 worker의 동시성 초과 요청의
multipart body를 읽기 전에 401/429를 반환합니다. body limiter는 잘못된 framing,
JSON/multipart 크기 초과, downstream 응답 이후의 추가 send를 fail closed로
처리합니다.

## 여행 상태와 동시성

운영에서는 `SQLiteStateStore.transaction()`이 `BEGIN IMMEDIATE` 후 singleton
snapshot을 `AppState`로 복원하고, 요청이 성공하면 versioned JSON으로 commit합니다.
요청이 예외로 종료되면 전체 변경이 rollback됩니다. 이 방식은 기존 서비스 API를
유지하면서 여러 worker의 lost update를 막지만 모든 여행 write를 직렬화하는
과도기 구조입니다.

OAuth state는 외부 Google 호출 동안 여행 write lock을 잡지 않도록 별도
`oauth_states` 테이블에서 짧은 원자 transaction으로 발급·1회 소비합니다.
SQLite 연결은 WAL, foreign keys, busy timeout을 설정하며 migration version이
패키지의 최신 SQL과 일치해야 readiness를 통과합니다.

## 인증과 소유권

- 운영의 모든 `/api/v1/trips...` operation은 Bearer JWT가 필요합니다.
- 여행 생성 시 JWT `sub`의 사용자 ID를 owner로 저장합니다.
- 목록은 owner의 여행만 반환하고 item/nested 경로는 owner가 아니면 404입니다.
- 회원 Memorial도 동일 user ID로 DB row와 로컬 파일 접근을 격리합니다.
- 개발 여행 API는 호환용 actor `0`을 허용하지만 운영 보안 계약으로 간주하지
  않습니다.

## 로컬 사진 저장

사진 원본은 `MEMORIAL_PHOTO_DIR/{user_id}/{uuid}.{ext}`에 저장하고 DB에는 이
상대 경로만 기록합니다. 경로 탈출, symlink, 비정규 파일, 사용자 디렉터리 불일치,
덮어쓰기를 거부합니다. 디렉터리 `0700`, 파일 `0600`을 생성·복구 시 강제합니다.
사진 root는 DB와 겹치지 않는 전용 디렉터리만 허용하고 알 수 없는 기존 항목이
있으면 권한 변경이나 복구 삭제 전에 거부합니다.

본문 전 요청 슬롯과 파일 크기 확인 후 upload lease를 SQLite에서 원자적으로
관리합니다. 파일 수·총 byte, 시간당 시도, 사용자/전역 동시성, 예약 byte를 포함한
디스크 watermark를 검사합니다. 삭제는 `.trash` hard-link staging과 DB
transaction을 결합하며, 시작 시 orphan, 만료 lease, 중단된 delete를 조정합니다.

## 데이터 불변식

- PATCH는 Pydantic `model_fields_set`을 기준으로 생략과 `null`을 구분합니다.
- 위도와 경도는 항상 함께 존재하거나 함께 `null`이어야 합니다.
- schedule의 `place_id`는 같은 여행의 wanted place만 참조합니다.
- wanted place 삭제 시 schedule·plan의 선택적 참조를 원자적으로 nullify합니다.
- 사진 시각은 UTC instant로 안정 정렬하고 사용자 계약상 `Asia/Tokyo`로
  정규화합니다. naive EXIF와 서버 fallback도 호스트 시간대와 무관합니다.
- AI planning DTO는 day index/date/time 관계와 POI 선호 day 참조를 검증합니다.

## 가용성과 오류

`/health`는 프로세스 liveness만, `/ready`는 운영 설정, DB 접근·migration,
사진 root의 전용 `.health` probe, disk watermark를 검사합니다. 공통 오류는
`{"detail": "..."}`로 정규화하며 인증 401, 없음 404, body/quota 413, media 415,
validation 422, rate/concurrency 429, upstream 502, dependency 503, storage 507을
OpenAPI와 런타임에 동일하게 노출합니다.

운영 백업은 SQLite 파일과 사진 root를 같은 시점에 보존해야 합니다. readiness는
백업, 복제, 다중 호스트 일관성을 대신하지 않습니다.
