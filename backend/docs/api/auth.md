# 인증 API

## 현재 범위

Google OAuth callback으로 로컬 사용자 레코드를 만들고 8시간 유효한 HS256
JWT를 발급합니다. 현재 JWT가 필수인 API는 `GET /api/v1/auth/me`와 회원 단위
Memorial API(`/api/v1/memorial/*`)입니다.
여행 관련 API는 프론트엔드 연동을 위한 개발 프로토타입 계약 때문에 아직
공개되어 있습니다.

공유 개발 서버나 외부 배포 전에는 여행 리소스에 사용자 소유권을 연결하고
라우터 인증 의존성을 추가해야 합니다.

## 흐름

```text
클라이언트
  -> GET /api/v1/auth/google/login
  <- 302 Google authorize URL + 서버 등록 state + HttpOnly state cookie
  -> Google 사용자 인증
  -> GET /api/v1/auth/google/callback?code=...&state=...
  -> backend가 query state와 브라우저 cookie를 비교하고 state를 1회 소비
  -> Google token/profile API 호출
  -> SQLite 사용자 upsert
  <- GoogleAuthResponse(user, access_token, token_type)
  -> GET /api/v1/auth/me (Authorization: Bearer <access_token>)
```

## Google 로그인 시작

`GET /api/v1/auth/google/login`

- 응답: `302 Found`
- Google authorize URL에 예측 불가능한 `state`를 포함합니다.
- 같은 값을 600초 동안 서버 메모리에 등록하고
  `chiwawa_oauth_state` 쿠키에도 저장합니다.
- 쿠키 기본값은 `HttpOnly`, `SameSite=Lax`, 600초, 경로
  `/api/v1/auth/google`입니다.
- 로컬 HTTP 개발 기본값은 `Secure=false`이며 HTTPS 환경에서는
  `GOOGLE_OAUTH_COOKIE_SECURE=true`로 설정해야 합니다.
- 로그인 시작 URL의 호스트와 `GOOGLE_REDIRECT_URI`의 호스트가 같아야 host-only
  state 쿠키가 callback에도 전달됩니다. 기본 예시는 둘 다 `localhost`입니다.

## Google callback

`GET /api/v1/auth/google/callback?code=...&state=...`

| 입력 | 필수 | 설명 |
| --- | --- | --- |
| query `code` | 예 | Google authorization code |
| query `state` | 예 | 로그인 시작 응답의 state |
| cookie `chiwawa_oauth_state` | 예 | 로그인 시작 브라우저를 결합하는 state cookie |

state는 서버에서 발급·등록한 값이어야 하며 callback에서 한 번 소비됩니다.
query state와 로그인 시작 브라우저의 HttpOnly 쿠키도 일치해야 합니다. 알 수
없거나 재사용되거나 쿠키와 불일치한 state는 Google API를 호출하기 전에
거부합니다.

현재 backend callback은 같은 브라우저가 Google redirect를 받는 웹 흐름입니다.
외부 브라우저가 `chiwawa://auth` 딥링크로 앱에 code를 넘기고 별도 Dio 클라이언트가
교환하는 기존 모바일 초안은 이 HttpOnly 쿠키를 전달할 수 없습니다. 모바일
연동 전에는 앱이 시작 state/PKCE verifier를 보관·검증하거나, 백엔드가 일회성
앱 교환 코드를 발급하는 방식으로 프론트와 계약을 함께 확정해야 합니다.

```json
{
  "message": "login successful",
  "provider": "google",
  "token_type": "bearer",
  "access_token": "<jwt>",
  "user": {
    "id": "1",
    "google_sub": "google-user-id",
    "email": "traveler@example.com",
    "name": "Prototype Traveler",
    "picture": null,
    "created_at": "2026-07-10T06:00:00Z",
    "last_login_at": "2026-07-10T06:00:00Z"
  }
}
```

| 상태 | 원인 |
| --- | --- |
| 400 | 알 수 없는·재사용된 state 또는 쿠키 불일치 |
| 422 | code/state/cookie 누락 또는 잘못된 query 형식 |
| 500 | Google 또는 JWT 필수 환경 설정 누락 |
| 502 | Google token 교환 또는 profile 응답 실패 |

## 현재 사용자

`GET /api/v1/auth/me`

`Authorization: Bearer <access_token>` 헤더가 필요합니다. 성공 응답은 `sub`,
`email`, `name`을 반환합니다. 토큰 누락, 만료, 서명 오류는 각각 401입니다.

JWT payload는 `sub`, `iat`, `exp`, `email`, `name`으로 구성되고 발급 후
8시간 유효합니다. 갱신 API는 없으므로 만료 시 다시 로그인합니다.

## 환경 설정

루트 `.env.example`을 기준으로 백엔드 디렉터리의 `.env` 또는 프로세스 환경
변수를 사용합니다. 프로세스 환경 변수가 `.env`보다 우선합니다.

| 환경 변수 | 기본값 | 설명 |
| --- | --- | --- |
| `GOOGLE_CLIENT_ID` | 없음 | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | 없음 | Google OAuth client secret |
| `GOOGLE_REDIRECT_URI` | 없음 | 등록된 callback URL |
| `JWT_SECRET` | 없음 | 최소 32자의 JWT 서명 키 |
| `GOOGLE_AUTH_DB_PATH` | `data/google_auth.db` | Google 사용자 SQLite 경로 |
| `GOOGLE_OAUTH_COOKIE_SECURE` | `false` | HTTPS에서 state cookie Secure 활성화 |
| `GOOGLE_OAUTH_STATE_TTL_SECONDS` | `600` | 서버 state와 cookie 수명, 60~3600초 |

인증 설정이 없어도 앱 시작, `/health`, API 문서, 여행 프로토타입 API는
동작합니다. Google 로그인과 JWT 발급 시점에만 필수 설정을 검사합니다.

authorization code와 state는 query string에 있으므로 개발 실행 예시는 Uvicorn
access log를 끕니다. 공유 환경에서는 reverse proxy/APM에서도 callback query를
기록하지 않거나 반드시 마스킹해야 합니다.

## 저장 위치

- 사용자 저장 서비스: `src/chiwawa_backend/services/auth.py`
- 패키지 SQL: `src/chiwawa_backend/sql/001_google_users.sql`
- 기본 런타임 DB: `data/google_auth.db` (Git 제외)
- OAuth 라우터: `src/chiwawa_backend/routers/auth.py`
- JWT 서비스: `src/chiwawa_backend/services/jwt_auth.py`
