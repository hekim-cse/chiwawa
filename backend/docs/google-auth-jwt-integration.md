# Google OAuth + JWT 인증 통합

## 범위

이 계약은 Chiwawa 앱의 구글 로그인 및 JWT 토큰 기반 인증 흐름을 정의한다.
프론트엔드는 Google OAuth 인증을 통해 사용자를 인증하고, 백엔드에서 발급한
JWT 토큰으로 이후의 모든 API 요청을 인증한다.

---

## 아키텍처

```
┌──────────────────────┐
│   Flutter App        │
└──────────┬───────────┘
           │
    (1) 로그인 요청
           │
           ├──→ GET /api/v1/auth/google/login
           │
           ├──→ 구글 OAuth 리다이렉트
           │    (사용자가 구글로 인증)
           │
           ├──→ Callback 수신 (code 파라미터)
           │
    (2) 토큰 교환
           │
           └──→ GET /api/v1/auth/google/callback?code=...
                └──→ 응답: {user, access_token}
                    └──→ JWT 토큰 로컬 저장
           
    (3) 인증된 요청
           │
           ├──→ 모든 API 요청에 토큰 첨부
           │    Authorization: Bearer <access_token>
           │
           └──→ GET /api/v1/auth/me
                └──→ 토큰 검증 및 사용자 정보 반환
```

---

## API 명세

### 1. Google 로그인 시작

**엔드포인트**: `GET /api/v1/auth/google/login`

**설명**: 사용자를 Google OAuth 인증 페이지로 리다이렉트한다.

**응답**:
- HTTP 302 Redirect
- Location: Google OAuth 인증 URL

---

### 2. Google 로그인 콜백

**엔드포인트**: `GET /api/v1/auth/google/callback`

**쿼리 파라미터**:

| 파라미터 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `code` | string | ✓ | Google OAuth 인증 코드 |
| `state` | string | | CSRF 보호용 상태값 |

**응답 (200 OK)**:

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `user` | object | 사용자 정보 객체 |
| `user.id` | string | 서비스 내부 사용자 ID |
| `user.google_sub` | string | Google의 고유 ID |
| `user.email` | string | 이메일 주소 |
| `user.name` | string | 사용자 이름 |
| `user.picture` | string | 프로필 사진 URL |
| `user.created_at` | string | 계정 생성 시간 (ISO 8601) |
| `user.last_login_at` | string | 마지막 로그인 시간 (ISO 8601) |
| `access_token` | string | JWT 토큰 |

**응답 예**:
```json
{
  "user": {
    "id": "123",
    "google_sub": "1234567890",
    "email": "user@gmail.com",
    "name": "John Doe",
    "picture": "https://lh3.googleusercontent.com/...",
    "created_at": "2026-07-09T12:34:56+00:00",
    "last_login_at": "2026-07-09T13:45:00+00:00"
  },
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjMiLCJpYXQiOjE2ODkwMDAwMDAsImV4cCI6MTY4OTAyODgwMCwiZW1haWwiOiJ1c2VyQGdtYWlsLmNvbSIsIm5hbWUiOiJKb2huIERvZSJ9..."
}
```

**에러 응답**:

| 상태 | 메시지 | 원인 |
| --- | --- | --- |
| 400 | authorization code is required | code 파라미터 누락 |
| 500 | Google OAuth is not configured | 서버 환경 변수 미설정 |

---

### 3. 현재 사용자 정보 조회

**엔드포인트**: `GET /api/v1/auth/me`

**인증**: 필수 (Bearer Token)

**헤더**:

| 헤더 | 값 |
| --- | --- |
| Authorization | Bearer &lt;access_token&gt; |

**응답 (200 OK)**:

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `sub` | string | 사용자 ID |
| `email` | string | 이메일 주소 |
| `name` | string | 사용자 이름 |

**응답 예**:
```json
{
  "sub": "123",
  "email": "user@gmail.com",
  "name": "John Doe"
}
```

**에러 응답**:

| 상태 | 메시지 | 원인 |
| --- | --- | --- |
| 401 | missing token | Authorization 헤더 누락 |
| 401 | token expired | 토큰 만료 (유효기간 8시간) |
| 401 | invalid token | 토큰 서명 검증 실패 |

---

## JWT 토큰

### 토큰 구조

JWT는 `header.payload.signature` 3개 부분으로 구성된다.

**Payload 필드**:

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `sub` | string | 사용자 ID |
| `iat` | integer | 토큰 발급 시간 (Unix Timestamp) |
| `exp` | integer | 토큰 만료 시간 (Unix Timestamp) - 발급 후 8시간 |
| `email` | string | 이메일 주소 |
| `name` | string | 사용자 이름 |

### 토큰 유효기간

- 발급 후 **8시간** 유효
- 만료된 토큰으로 요청 시 401 응답
- 갱신 엔드포인트 없음 (만료 시 재로그인 필요)

---

## 환경 설정

백엔드 서버 실행 시 다음 환경 변수 설정 필요:

| 환경 변수 | 예시 | 설명 |
| --- | --- | --- |
| `GOOGLE_CLIENT_ID` | `xxx.apps.googleusercontent.com` | Google OAuth Client ID |
| `GOOGLE_CLIENT_SECRET` | `secret-key-string` | Google OAuth Client Secret |
| `GOOGLE_REDIRECT_URI` | `http://localhost:8000/api/v1/auth/google/callback` | 콜백 URL |
| `JWT_SECRET` | `long-random-secret-string` | JWT 서명용 비밀키 (프로덕션: 변경 필수) |
| `GOOGLE_AUTH_DB_PATH` | `./data/google_auth.db` | 사용자 DB 경로 (선택사항) |

---

## 코드 위치

- **라우터**: `backend/src/chiwawa_backend/routers/auth.py`
- **JWT 유틸**: `backend/src/chiwawa_backend/services/jwt_auth.py`
- **사용자 저장**: `backend/src/chiwawa_backend/services/auth.py`
- **스키마**: `backend/src/chiwawa_backend/schemas/auth.py`
- **테스트**: `backend/tests/test_google_auth.py`

---

## 통합 경계

프론트엔드는 다음 조건에서 이 인증 API를 사용할 수 있다:

1. WebView 또는 시스템 브라우저로 `/api/v1/auth/google/login`에 접근
2. 사용자 구글 인증 완료 후 콜백 URL의 `code` 파라미터 추출
3. 백엔드 `/api/v1/auth/google/callback` 호출하여 `access_token` 수신
4. 이후 모든 API 요청의 Authorization 헤더에 토큰 첨부

---

**작성일**: 2026-07-09  
**버전**: 1.0  
**작성자**: Chiwawa Backend Team
