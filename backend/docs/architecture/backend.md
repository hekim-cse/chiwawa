# 백엔드 구조

현재 백엔드는 FastAPI 기반 개발 프로토타입입니다. HTTP 계약, Pydantic 경계,
서비스 로직, 저장 상태를 기능별 모듈로 분리합니다.

## 모듈 구조

| 영역 | 경로 | 역할 |
| --- | --- | --- |
| 앱 엔트리 | `src/chiwawa_backend/main.py` | 앱 생성, 라우터·예외 핸들러 등록, 문서 진입점 |
| 설정 | `src/chiwawa_backend/config.py` | `.env`와 환경 변수를 읽는 타입 설정, 필수 인증 설정 검사 |
| 라우터 | `src/chiwawa_backend/routers/` | HTTP 경로와 요청·응답 모델 연결 |
| 스키마 | `src/chiwawa_backend/schemas/` | frozen/extra-forbid Pydantic v2 경계 모델 |
| 서비스 | `src/chiwawa_backend/services/` | 여행, 장소, 일정, 추천, 인증, 기록 로직 |
| 프로토타입 상태 | `src/chiwawa_backend/state.py` | UUID ID와 인메모리 도메인 저장소 |
| 인증 스키마 | `src/chiwawa_backend/sql/001_google_users.sql` | wheel에 포함되는 Google 사용자 SQLite 스키마 |
| 런타임 인증 DB | `data/google_auth.db` | 자동 생성되고 Git에서 제외되는 로컬 파일 |

## 요청 처리 흐름

```text
HTTP request
  -> router
  -> Pydantic request validation
  -> service domain validation
  -> AppState or SQLite auth storage
  -> Pydantic response model
  -> HTTP response
```

스키마 수준 오류와 날짜·시간 같은 도메인 불변식 오류는 422, 없는 리소스는
404로 변환합니다. 인증 설정은 앱 시작 시 강제하지 않고 Google 로그인 또는
JWT 작업 시점에 검사하므로 비인증 개발 API와 문서는 독립적으로 실행됩니다.

## 상태와 동시성

- 여행 도메인의 `AppState`는 앱 인스턴스마다 생성되며 재시작 시 초기화됩니다.
- ID는 UUID 기반이라 동시 요청의 읽기-수정-쓰기 카운터 충돌이 없습니다.
- AppState를 읽고 쓰는 서비스 연산은 동일한 재진입 잠금을 사용해 컬렉션 순회와
  변경이 충돌하지 않습니다.
- 계획 확정은 모든 stop을 먼저 검증한 뒤 한 번만 일정으로 투영되어 실패 시
  부분 저장이 없고 반복 요청이 멱등적입니다.
- Google 사용자 SQLite 연결은 요청 단위로 열고 트랜잭션 후 명시적으로 닫습니다.
- SQLite 스키마는 `importlib.resources`로 읽으므로 설치된 wheel에서도 동작합니다.

## 프로토타입 구현 경계

| 기능 | 현재 동작 | 실제 연동 시 교체 지점 |
| --- | --- | --- |
| 사진 장소 검색 | 여행 도시 기반 고정 후보 생성 | 사진 인식·장소 검색 provider |
| AI 일정 | 우선순위, pace, 시간창 기반 순차 휴리스틱 | AI planner adapter |
| 동선 최적화 | 우선순위 정렬과 추정 이동시간 | 지도 route provider |
| 주변 추천 | 위치 요청을 받는 결정적 추천 | 장소·지도 nearby provider |
| 빈 시간 추천 | 지역명과 시간창 기반 고정 산책 추천 | 장소·영업시간 recommendation provider |

현재 서비스 이름과 API 계약은 제품 흐름 검증용이며 외부 API 호출이나 실제 AI
추론을 보장하지 않습니다.

## 인증 경계

- Google 로그인 state를 서버 메모리에 짧게 등록해 한 번만 소비합니다. 같은
  브라우저의 HttpOnly 쿠키와 query state를 비교한 뒤 외부 token API를
  호출합니다. 별도 앱 HTTP 클라이언트 흐름은 PKCE/state 계약 조정 전까지
  지원하지 않습니다.
- JWT 공개 기본 키는 없으며 최소 32자의 명시적 `JWT_SECRET`이 필요합니다.
- 현재 보호 경로는 `/api/v1/auth/me`뿐입니다.
- 외부 또는 공유 환경으로 옮기기 전에 여행 리소스의 사용자 소유권,
  인증 의존성, 영속 DB, 마이그레이션을 추가해야 합니다.

현재 여행 도메인은 최대 31일과 `Asia/Tokyo` 현지 시각을 기준으로 합니다.
다른 국가·시간대를 지원할 때는 trip timezone 필드를 계약에 추가해야 합니다.

## 확장 기준

- 라우터는 HTTP 계약에 집중하고 비즈니스 규칙은 서비스에 둡니다.
- 외부 공급자 연동은 서비스 아래 adapter 경계로 추가합니다.
- `AppState`를 repository/ORM 계층으로 교체할 때 라우터 모델은 유지합니다.
- 라우트나 DTO 변경 시 `docs/api/reference.md`, 관련 상세 문서, OpenAPI 테스트를
  함께 갱신합니다.
