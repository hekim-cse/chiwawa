# Backend Production Hardening Design

## Goal

`backend/`만 수정해 현재 FastAPI 프로토타입을 단일 호스트 다중 워커로
외부 배포할 수 있는 구조로 만든다. 사진은 S3가 아니라 설정된 로컬 영속
디렉터리에 저장한다. 프론트엔드와 AI 저장소는 수정하지 않는다.

## Deployment boundary

애플리케이션은 두 실행 프로필을 갖는다.

- `development`: 기존 로컬 개발 흐름을 유지한다. 여행 API는 익명 actor를
  사용하고 여행 상태는 프로세스 메모리에 둔다.
- `production`: JWT 인증, 사용자별 여행 소유권, SQLite 상태 영속화,
  secure OAuth cookie, 명시적 데이터베이스·사진 경로를 강제한다.

프로덕션 지원 범위는 한 호스트 안의 여러 Uvicorn worker다. 모든 worker가
같은 SQLite 파일과 사진 디렉터리를 사용한다. 여러 호스트 또는 컨테이너
replica는 로컬 파일 요구와 양립하지 않으므로 지원 범위 밖이다.

## Considered approaches

1. PostgreSQL, Redis, object storage: 수평 확장에는 가장 적합하지만 S3가
   허용되지 않고 현재 프로토타입보다 운영 의존성과 변경량이 지나치게 크다.
2. SQLite, in-memory OAuth, local files: 변경량은 작지만 worker handoff에서
   여행과 OAuth state가 깨지므로 목표를 충족하지 못한다.
3. Shared local SQLite, local files: 단일 호스트 제약 안에서 상태와 OAuth를
   worker 간 공유하고 기존 동기 서비스 API를 유지할 수 있다. 이 방식을
   선택한다.

## State and ownership

현재 서비스가 사용하는 frozen Pydantic DTO 컬렉션은 `StateSnapshot`으로
직렬화한다. 프로덕션 `StateDep`는 function-scope yield dependency로 다음
요청 transaction을 수행한다.

1. SQLite `BEGIN IMMEDIATE`로 다른 worker의 writer와 직렬화한다.
2. 최신 snapshot을 request-local `AppState`로 복원한다.
3. 기존 router와 service가 같은 dependency instance를 재사용한다.
4. 성공하면 새 snapshot을 upsert하고 응답 전 commit한다.
5. 실패하면 rollback한다.

기존 `synchronized`는 한 요청 안의 중첩 서비스 호출과 개발 모드의 thread
안전성을 계속 담당한다. SQLite transaction은 dependency가 한 번만 소유한다.

OAuth state는 전체 여행 snapshot과 분리된 `oauth_states` 테이블에 저장한다.
발급과 1회 소비는 각각 짧은 SQLite transaction이므로 Google provider HTTP
호출 중에는 write lock을 잡지 않는다. 용량이 찼을 때 유효한 state를
축출하지 않고 429 오류로 신규 발급을 거절한다.

Snapshot에는 `trip_owners`를 포함한다. 개발 actor는 `0`이며, 프로덕션
actor는 JWT `sub`다. 생성·목록·단건 여행 API는 owner를 적용하고 모든
trip-scoped router는 공통 접근 dependency로 소유권을 먼저 검사한다.

## Database migrations

패키지의 `src/chiwawa_backend/sql/`만 migration source of truth로 사용한다.
파일명의 숫자 prefix가 version이며 `schema_migrations` ledger에 적용 이력을
기록한다. 각 미적용 script와 ledger insert는 `BEGIN IMMEDIATE` 안에서 함께
성공하거나 rollback한다. 프로세스별 초기화 cache는 반복 파일 읽기를 막고,
ledger와 SQLite lock은 여러 worker의 동시 startup을 안전하게 만든다.

애플리케이션 lifespan은 database migration과 로컬 사진 root 준비를 한다.
직접 서비스를 호출하는 테스트 호환성을 위해 `connect()`의 lazy initialization도
유지한다.

## Request admission and upload security

FastAPI dependency resolution보다 바깥에 pure ASGI middleware를 둔다.

- 회원 사진 multipart 경로는 Authorization header를 먼저 검증한다. 무토큰
  요청은 body를 읽기 전에 401을 반환한다.
- `Content-Length`를 선검사하고 chunked body는 `receive` wrapper가 실제
  누적 byte를 제한한다.
- 일반 JSON과 multipart에 서로 다른 최대 request size를 사용한다.
- 모든 응답에 request ID와 기본 보안 헤더를 추가한다.

사진 저장 admission은 SQLite `BEGIN IMMEDIATE` 안에서 사용자별 사진 수,
총 byte, 최근 업로드 수를 검사한다. 로컬 디스크 여유 공간이 watermark보다
작으면 507을 반환한다. 이로써 여러 worker의 동시 업로드도 quota를 넘지 않는다.

## Local photo storage

`LocalPhotoStore`가 파일 경계만 소유한다.

- root와 사용자 디렉터리는 `0700`, 사진 파일은 `0600`을 강제한다.
- UUID 이름과 `O_CREAT | O_EXCL`로 경로 조작과 overwrite를 막는다.
- DB에는 root 기준 상대 경로만 저장한다.
- 다운로드 시 resolve된 경로가 root 내부인지 다시 확인한다.
- 삭제는 같은 filesystem의 root 내부 trash에 hard-link를 먼저 동기화한 뒤
  원본을 제거하고 DB row를 삭제한다. DB 실패 시 원위치로 복구하며, commit 뒤
  trash unlink 실패는 요청 정합성을 깨지 않고 다음 startup 정리 대상으로 남긴다.

Pillow가 감지한 실제 format으로 MIME을 저장한다. decompression-bomb warning과
error, 허용 pixel·dimension 초과를 모두 415로 거절한다.

## Time contract

회원 사진의 naive EXIF/form 시간은 `Asia/Tokyo`로 해석한다. aware 시간도
Tokyo local time으로 정규화해 응답용 `taken_at`과 `local_date`를 만들고,
별도 UTC instant를 저장해 timeline을 정렬한다. fallback도 host timezone과
무관하게 Tokyo 현재 시각을 사용한다.

AI DTO는 backend 파일만 변경해 현재 AI wire contract에 맞춘다.

- `PARTIAL_SUCCESS` 상태와 route option/timeline 구조를 지원한다.
- day 시간은 offset 없는 분 단위이며 `start < end`다.
- day index/date는 고유하고, POI preferred day는 실제 day를 참조한다.
- 빈 POI와 정의되지 않은 category를 거절한다.

## PATCH and reference integrity

모든 PATCH는 Pydantic `model_fields_set`으로 생략과 명시적 null을 구분한다.
생략은 보존, nullable 필드의 null은 삭제, non-null 필드의 null은 422다.
좌표는 항상 두 값이 함께 존재하거나 함께 비어 있어야 한다.

Schedule의 `place_id`는 같은 trip의 wanted place만 허용한다. 장소 삭제 시
schedule과 plan snapshot의 `place_id`를 null로 바꾸고 확인 캐시를 제거해
dangling reference가 남지 않게 한다. 표시 이름과 과거 일정 내용은 보존한다.

## Operations and API contract

- `/health`: 프로세스 liveness만 나타낸다.
- `/ready`: migration이 적용된 DB 접근, 사진 root 쓰기 가능성, 디스크
  watermark, production 필수 설정을 검사한다. 실패는 503이다.
- private photo 응답은 `Cache-Control: private, no-store`와
  `X-Content-Type-Options: nosniff`를 포함한다.
- router별 실제 401/404/413/415/422/429/500/507 오류를 `ErrorResponse`로
  OpenAPI에 선언하고 binary file response도 명시한다.

## Verification

각 행동 변경은 실패하는 regression test를 먼저 실행한 뒤 최소 구현으로
통과시킨다. 최종 gate는 다음과 같다.

1. persistence: 서로 다른 `AppState`/app instance 간 여행과 OAuth handoff
2. security: 무토큰 multipart body 0 byte 소비, chunked size 제한
3. storage: quota/rate/watermark, 0700/0600, trash delete recovery
4. domain: cross-trip place 거절, delete 후 dangling 없음, PATCH null
5. time/contract: mixed offset UTC ordering, host timezone 독립, AI invariants
6. operations: readiness failure, exact OpenAPI security/error contract
7. `make check`, wheel build, 설치 wheel 실행
8. live Uvicorn에서 인증 오류, 핵심 trip flow, upload/download/delete,
   두 worker가 공유하는 상태를 실제 HTTP로 확인

## Non-goals

- 프론트엔드 또는 AI 저장소 수정
- S3 또는 다른 object storage 도입
- 여러 호스트에 걸친 horizontal scaling
- 외부 AI/지도 공급자 실제 연동
- Git commit, push, PR 생성
