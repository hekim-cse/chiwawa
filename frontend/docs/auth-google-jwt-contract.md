# Google OAuth + JWT 인증 계약

작성일: 2026-07-09  
버전: 1.0

## 범위

Chiwawa 앱의 Google OAuth 로그인과 JWT 토큰 기반 API 인증 흐름을 정의한다.
프론트엔드는 Google OAuth 인증 후 백엔드가 발급한 `access_token`을 저장하고,
이후 인증이 필요한 API 요청에 `Authorization: Bearer <access_token>` 헤더를 첨부한다.

## 인증 흐름

```text
Flutter App
  -> GET /api/v1/auth/google/login
  -> Google OAuth 인증 페이지로 302 redirect
  -> 사용자가 Google 인증
  -> callback URL에서 code 수신
  -> GET /api/v1/auth/google/callback?code=...
  <- { user, access_token }
  -> access_token 로컬 저장
  -> 이후 API 요청에 Authorization: Bearer <access_token> 첨부
  -> GET /api/v1/auth/me 로 토큰 검증 및 사용자 정보 조회
```

## API 명세

### Google 로그인 시작

- Method: `GET`
- Path: `/api/v1/auth/google/login`
- 동작: 사용자를 Google OAuth 인증 페이지로 redirect한다.
- 응답: `302 Redirect`

### Google 로그인 콜백

- Method: `GET`
- Path: `/api/v1/auth/google/callback`

Query:

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `code` | `string` | 예 | Google OAuth 인증 코드 |
| `state` | `string` | 아니오 | CSRF 보호용 상태값 |

Response `200 OK`:

| 필드 | 타입 | 설명 |
|------|------|------|
| `user` | `object` | 사용자 정보 객체 |
| `user.id` | `string` | 서비스 내부 사용자 ID |
| `user.google_sub` | `string` | Google 고유 ID |
| `user.email` | `string` | 이메일 주소 |
| `user.name` | `string` | 사용자 이름 |
| `user.picture` | `string` | 프로필 사진 URL |
| `user.created_at` | `string` | 계정 생성 시간, ISO 8601 |
| `user.last_login_at` | `string` | 마지막 로그인 시간, ISO 8601 |
| `access_token` | `string` | JWT 토큰 |

Error:

| 상태 | 메시지 | 원인 |
|------|--------|------|
| `400` | `authorization code is required` | `code` 파라미터 누락 |
| `500` | `Google OAuth is not configured` | 서버 환경 변수 미설정 |

### 현재 사용자 정보 조회

- Method: `GET`
- Path: `/api/v1/auth/me`
- Auth: 필수

Header:

```http
Authorization: Bearer <access_token>
```

Response `200 OK`:

| 필드 | 타입 | 설명 |
|------|------|------|
| `sub` | `string` | 사용자 ID |
| `email` | `string` | 이메일 주소 |
| `name` | `string` | 사용자 이름 |

Error:

| 상태 | 메시지 | 원인 |
|------|--------|------|
| `401` | `missing token` | Authorization 헤더 누락 |
| `401` | `token expired` | 토큰 만료 |
| `401` | `invalid token` | 토큰 서명 검증 실패 |

## JWT 토큰

Payload:

| 필드 | 타입 | 설명 |
|------|------|------|
| `sub` | `string` | 사용자 ID |
| `iat` | `integer` | 토큰 발급 시간, Unix timestamp |
| `exp` | `integer` | 토큰 만료 시간, Unix timestamp |
| `email` | `string` | 이메일 주소 |
| `name` | `string` | 사용자 이름 |

- 유효기간: 발급 후 8시간
- 만료 시 응답: `401 token expired`
- 갱신 엔드포인트 없음. 만료 시 재로그인한다.

## 백엔드 환경 변수

| 환경 변수 | 예시 | 설명 |
|-----------|------|------|
| `GOOGLE_CLIENT_ID` | `xxx.apps.googleusercontent.com` | Google OAuth Client ID |
| `GOOGLE_CLIENT_SECRET` | `secret-key-string` | Google OAuth Client Secret |
| `GOOGLE_REDIRECT_URI` | `http://localhost:8000/api/v1/auth/google/callback` | 콜백 URL |
| `JWT_SECRET` | `long-random-secret-string` | JWT 서명용 비밀키 |
| `GOOGLE_AUTH_DB_PATH` | `./data/google_auth.db` | 사용자 DB 경로 |

## 백엔드 코드 위치

- 라우터: `backend/src/chiwawa_backend/routers/auth.py`
- JWT 유틸: `backend/src/chiwawa_backend/services/jwt_auth.py`
- 사용자 저장: `backend/src/chiwawa_backend/services/auth.py`
- 스키마: `backend/src/chiwawa_backend/schemas/auth.py`
- 테스트: `backend/tests/test_google_auth.py`

## 프론트 통합 메모

- 인증 시작은 `/api/v1/auth/google/login`으로 이동한다.
- 프론트는 OAuth `code`를 확보한 뒤 `/api/v1/auth/google/callback?code=...`을 호출한다.
- 응답의 `access_token`을 로컬 저장소에 저장한다.
- 모든 인증 API 요청에는 `Authorization: Bearer <access_token>`을 첨부한다.
- `GET /api/v1/auth/me`로 앱 시작 시 토큰 유효성과 사용자 정보를 확인한다.
- 시스템 브라우저만 사용할 경우 프론트가 `code`를 받으려면 앱/웹으로 돌아오는 redirect URL 합의가 필요하다. 백엔드 callback URL에 그대로 머무르는 구조라면 프론트가 code를 직접 가로채기 어렵다.
