# 인증 API

## 운영 계약

Google OAuth callback으로 로컬 사용자를 upsert하고 8시간 유효한 HS256 JWT를
발급합니다. 운영(`APP_ENV=production`)에서는 다음 경로가 모두 Bearer 인증
대상입니다.

- `GET /api/v1/auth/me`
- 모든 `/api/v1/trips...` 여행·장소·일정·추천·여행 기록 API
- 모든 `/api/v1/memorial...` 회원 사진 API

여행 생성 시 JWT `sub`의 사용자 ID를 owner로 저장합니다. 목록에는 본인 여행만
나오며 다른 사용자의 여행 또는 nested resource 접근은 404로 처리합니다. 개발
모드의 여행 API는 기존 로컬 연동을 위해 actor `0`을 허용하지만 운영 보안 계약은
항상 Bearer + ownership입니다.

## OAuth 흐름

```text
browser
  -> GET /api/v1/auth/google/login
  <- 302 Google authorize URL + HttpOnly state cookie
  -> Google authentication
  -> GET /api/v1/auth/google/callback?code=...&state=...
  -> cookie/query 일치 확인 + SQLite state 원자적 1회 소비
  -> Google token/profile API
  -> SQLite user upsert + JWT 발급
  <- GoogleAuthResponse
```

OAuth state는 여행 snapshot과 분리된 SQLite `oauth_states` 테이블에 만료 시각과
함께 저장됩니다. 여러 worker 중 어느 worker가 callback을 받아도 소비할 수 있고,
동시에 두 callback이 와도 정확히 하나만 성공합니다. state transaction은 Google
외부 호출 전에 끝나므로 외부 응답을 기다리는 동안 SQLite write lock을 잡지
않습니다.

## 로그인 시작

`GET /api/v1/auth/google/login`

- 응답: `302 Found`
- 예측 불가능한 state를 SQLite에 저장하고 authorize URL과
  `chiwawa_oauth_state` 쿠키에 같은 값을 넣습니다.
- 쿠키는 `HttpOnly`, `SameSite=Lax`, `/api/v1/auth/google` 경로이며 TTL은
  `GOOGLE_OAUTH_STATE_TTL_SECONDS`입니다.
- 운영에서는 `GOOGLE_OAUTH_COOKIE_SECURE=true`가 강제됩니다.
- login URL과 callback URL의 호스트가 같아야 host-only cookie가 전달됩니다.

## Google callback

`GET /api/v1/auth/google/callback?code=...&state=...`

query의 `state`, HttpOnly cookie, SQLite에 발급된 미사용 state가 모두 일치해야
합니다. 알 수 없음, 만료, 재사용, cookie 불일치는 Google API 호출 전에
거부합니다.

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
| 400 | state 알 수 없음·만료·재사용 또는 cookie 불일치 |
| 422 | 필수 query/cookie 형식 오류 |
| 502 | Google token/profile upstream 실패 |

현재 callback은 Google redirect와 HttpOnly cookie를 같은 브라우저가 처리하는 웹
흐름입니다. 모바일 딥링크가 별도 HTTP client에서 code를 교환하려면 PKCE 또는
일회성 앱 교환 코드 계약을 프론트와 별도로 정의해야 합니다.

## 현재 사용자와 JWT

`GET /api/v1/auth/me`

`Authorization: Bearer <access_token>`이 필요합니다. JWT payload는 `sub`, `iat`,
`exp`, `email`, `name`이며 발급 후 8시간 유효합니다. 토큰 누락, 만료, 위조,
SQLite 정수 범위를 벗어난 `sub`는 401입니다. refresh API는 없습니다.

## 환경 설정

| 환경 변수 | 개발 기본값 | 운영 규칙 |
| --- | --- | --- |
| `APP_ENV` | `development` | `production`으로 명시 |
| `DATABASE_PATH` | 미설정 | 절대 경로 필수 |
| `GOOGLE_AUTH_DB_PATH` | `data/google_auth.db` | 개발 호환 fallback |
| `GOOGLE_CLIENT_ID` | 없음 | 필수 |
| `GOOGLE_CLIENT_SECRET` | 없음 | 필수 |
| `GOOGLE_REDIRECT_URI` | 없음 | 필수 HTTPS callback |
| `GOOGLE_OAUTH_COOKIE_SECURE` | `false` | `true` 필수 |
| `GOOGLE_OAUTH_STATE_TTL_SECONDS` | `600` | 60~3600초 |
| `JWT_SECRET` | 없음 | 32자 이상 필수 |

운영 설정은 `/ready`에서 검사되며 불완전하면 503입니다. liveness와 문서는
유지되지만 readiness를 통과하기 전에는 트래픽을 보내면 안 됩니다. 개발에서는
OAuth/JWT를 실제로 사용할 때 필요한 값만 검사합니다. callback query에는 code와
state가 있으므로 Uvicorn, proxy, APM access log에서 query를 기록하지 않거나
마스킹해야 합니다.

SQLite DB에는 사용자, OAuth state, 여행 snapshot, 사진 메타데이터와 업로드
lease가 함께 저장됩니다. 운영에서는 `DATABASE_PATH` 하나만 정본으로 사용합니다.
