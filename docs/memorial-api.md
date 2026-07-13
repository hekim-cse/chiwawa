# Memorial API 명세서

여행 추억(Memorial) 기능의 백엔드 API 명세.

## 기능 개요

- 사용자가 폰으로 찍은 사진을 업로드하면, 사진에 포함된 **촬영 시각(EXIF DateTimeOriginal)** 과 **촬영 위치(EXIF GPS)** 를 서버가 자동으로 추출해 저장한다.
- 프론트엔드 흐름: **캘린더 → 날짜 선택 → 지도 표시 → 시간순으로 치와와가 걸어가며 발자국 애니메이션 → 발자국 클릭 시 사진 표시**
  - 캘린더 화면: `GET /calendar` 로 사진이 있는 날짜(개수 포함)를 받아 달력에 표시한다.
  - 날짜 선택: `GET /days/{day}` 로 해당 날짜의 사진을 **촬영 시각 오름차순**으로 받는다. 응답의 순서(및 `seq` 필드)가 곧 발자국 애니메이션 순서다.
  - 발자국 클릭: 각 항목의 `file_url` 로 원본 사진을 내려받아 표시한다.
- Memorial은 **회원(google_users) 단위**로 관리된다. 모든 API는 로그인(JWT)이 필요하고, 자신의 사진만 조회/수정/삭제할 수 있다.
- 지도 타일 렌더링과 발자국 애니메이션은 프론트엔드(Google Maps SDK) 담당이며, 백엔드는 위경도·순서·주소 라벨을 제공한다.

## 인증

모든 엔드포인트는 아래 헤더가 필요하다. (토큰은 `GET /api/v1/auth/google/callback` 응답의 `access_token`)

```
Authorization: Bearer {access_token}
```

- 토큰이 없거나 유효하지 않으면 `401 {"detail": "..."}`.
- JWT `sub` 클레임 = `google_users.id`.

## 데이터베이스

SQLite (`backend/data/google_auth.db`, `GOOGLE_AUTH_DB_PATH` 환경변수로 변경 가능).
스키마 파일: `backend/sql/002_memorial_photos.sql`

```sql
CREATE TABLE IF NOT EXISTS memorial_photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES google_users (id) ON DELETE CASCADE,
    file_name TEXT NOT NULL,          -- 업로드 당시 원본 파일명
    stored_path TEXT NOT NULL,        -- 서버 저장 경로 (내부용)
    content_type TEXT NOT NULL,       -- image/jpeg, image/png, image/heic ...
    taken_at TEXT NOT NULL,           -- 촬영 시각, ISO 8601
    latitude REAL,                    -- 위도 (없으면 NULL)
    longitude REAL,                   -- 경도 (없으면 NULL)
    address TEXT,                     -- 역지오코딩된 주소 (없으면 NULL)
    memo TEXT,
    created_at TEXT NOT NULL          -- 업로드 시각, ISO 8601(UTC)
);

CREATE INDEX IF NOT EXISTS idx_memorial_photos_user_taken
    ON memorial_photos (user_id, taken_at);
```

- **외래키**: `user_id → google_users.id` (`ON DELETE CASCADE`, `PRAGMA foreign_keys = ON`). 회원 탈퇴 시 사진 레코드도 함께 삭제된다.
- 이미지 파일 본체는 DB가 아니라 `backend/data/memorial_photos/{user_id}/{uuid}.{ext}` 에 저장한다. (`MEMORIAL_PHOTO_DIR` 환경변수로 변경 가능)

## 메타데이터 결정 규칙

`taken_at`, `latitude`, `longitude` 는 아래 우선순위로 결정한다.

| 우선순위 | 출처 | 비고 |
|---|---|---|
| 1 | 업로드 폼 필드 | 클라이언트가 명시적으로 보낸 값 |
| 2 | 사진 EXIF | `DateTimeOriginal`(+`OffsetTimeOriginal`), GPS IFD |
| 3 | 기본값 | `taken_at` → 서버 수신 시각(UTC), 위경도 → `null` |

- EXIF를 읽을 수 없는 파일(스크린샷, 메신저로 받은 사진 등)도 업로드는 성공한다. 위치가 없는 사진은 지도 발자국에서는 제외하고 목록에만 노출하는 것을 권장.
- 지원 포맷: JPEG, PNG, WEBP, HEIC/HEIF (그 외 `image/*` 도 저장은 되지만 EXIF 추출은 보장하지 않음). 이미지가 아닌 파일은 `415`.

## 역지오코딩 (주소 라벨)

- 위경도가 확정되면 서버가 **Google Geocoding API** 로 주소 문자열을 조회해 `address` 에 저장한다. (타깃 지역: 오사카, 응답 언어 `ko`)
- `.env` 의 `GOOGLE_MAPS_API_KEY` 가 설정된 경우에만 동작하며, 키가 없거나 호출이 실패하면 `address: null` 로 저장되고 업로드는 정상 진행된다.
- 프론트엔드 지도 표시는 위경도만으로 가능하므로 `address` 는 발자국/사진의 부가 라벨 용도다.

## 공통 사항

- Base URL: `/api/v1/memorial`
- 날짜는 `YYYY-MM-DD`, 시각은 ISO 8601 (`2026-07-01T10:30:00+09:00`).
- 에러 응답 형식: `{"detail": "..."}`

| 상태 코드 | 의미 |
|---|---|
| 401 | 토큰 없음/만료/위조 |
| 404 | 리소스 없음 또는 다른 회원의 리소스 |
| 415 | 이미지가 아닌 파일 업로드 |
| 422 | 요청 형식 오류 (필드 검증 실패) |

### MemorialPhoto 객체

```json
{
  "id": 12,
  "file_name": "IMG_0301.jpg",
  "content_type": "image/jpeg",
  "taken_at": "2026-07-01T10:30:00+09:00",
  "latitude": 34.6687,
  "longitude": 135.5031,
  "address": "일본 오사카부 오사카시 주오구 도톤보리...",
  "memo": "도톤보리에서 점심",
  "file_url": "/api/v1/memorial/photos/12/file",
  "created_at": "2026-07-09T02:11:45+00:00"
}
```

---

## 1. 사진 업로드

```
POST /api/v1/memorial/photos
Content-Type: multipart/form-data
```

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `file` | file | O | 이미지 파일 |
| `taken_at` | string(ISO 8601) | X | 촬영 시각 재정의 |
| `latitude` | number (-90~90) | X | 위도 재정의 |
| `longitude` | number (-180~180) | X | 경도 재정의 |
| `memo` | string | X | 메모 |

**응답 `201 Created`**: `MemorialPhoto`

EXIF 추출에 실패해도 201로 성공하며, 메타데이터 결정 규칙의 기본값이 적용된다.

## 2. 캘린더 조회 (사진이 있는 날짜)

```
GET /api/v1/memorial/calendar?year=2026&month=7
```

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `year` | int (2000~2100) | O | 연도 |
| `month` | int (1~12) | O | 월 |

**응답 `200 OK`** — 사진이 1장 이상 있는 날짜만 포함, 날짜 오름차순:

```json
{
  "year": 2026,
  "month": 7,
  "days": [
    { "day": "2026-07-01", "photo_count": 5 },
    { "day": "2026-07-02", "photo_count": 3 }
  ]
}
```

## 3. 날짜별 타임라인 조회 (지도 발자국)

```
GET /api/v1/memorial/days/{day}      # 예: /days/2026-07-01
```

**응답 `200 OK`** — `taken_at` 오름차순 정렬. `seq`(0부터)가 발자국 애니메이션 순서:

```json
{
  "day": "2026-07-01",
  "items": [
    { "seq": 0, "photo": { ...MemorialPhoto (10:30 촬영) } },
    { "seq": 1, "photo": { ...MemorialPhoto (12:05 촬영) } }
  ]
}
```

사진이 없는 날짜는 `items: []` 로 200 응답.

## 4. 사진 메타데이터 단건 조회

```
GET /api/v1/memorial/photos/{photo_id}
```

**응답 `200 OK`**: `MemorialPhoto` / 없거나 남의 사진이면 `404`.

## 5. 사진 원본 파일 조회 (발자국 클릭)

```
GET /api/v1/memorial/photos/{photo_id}/file
```

**응답 `200 OK`**: 이미지 바이너리 (`Content-Type`: 업로드 당시 타입)

## 6. 사진 정보 수정

```
PATCH /api/v1/memorial/photos/{photo_id}
Content-Type: application/json
```

```json
{ "taken_at": "...", "latitude": 34.7, "longitude": 135.5, "memo": "..." }
```

모든 필드 선택. 보낸 필드만 수정된다. 위경도가 바뀌면 주소를 다시 조회한다.
**응답 `200 OK`**: 수정된 `MemorialPhoto`.

## 7. 사진 삭제

```
DELETE /api/v1/memorial/photos/{photo_id}
```

**응답 `204 No Content`** — DB 레코드와 저장된 파일이 함께 삭제된다.

---

## 참고

- 기존 `POST/GET /api/v1/trips/{trip_id}/memorial/*` (인메모리 프로토타입)는 당분간 유지하되, 본 명세의 회원 단위 API가 정식 Memorial API다.
- 프론트엔드 요약: 캘린더 화면 진입 시 `2. 캘린더 조회` → 날짜 탭 시 `3. 날짜별 타임라인` → 응답 순서대로 발자국을 찍으며 치와와 이동 → 발자국 탭 시 `5. 원본 파일` 표시.
