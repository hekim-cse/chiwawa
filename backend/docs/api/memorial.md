# Memorial API

## 현재 범위

여행 추억(Memorial) 사진을 회원 단위로 저장하고 캘린더와 날짜별 타임라인으로
조회하는 API입니다. 사진을 업로드하면 서버가 EXIF의 촬영
시각(`DateTimeOriginal`)과 GPS 위치를 추출해 저장하고, 위경도가 확정되면
Google Geocoding API로 주소 라벨을 조회해 함께 저장합니다.

모든 엔드포인트는 JWT Bearer 인증이 필요하며 자신의 사진만 조회·수정·삭제할
수 있습니다. 지도 타일 렌더링과 발자국 애니메이션은 프론트엔드(Google Maps
SDK) 담당이고, 백엔드는 위경도·순서·주소 라벨을 제공합니다.

기존 여행 단위 인메모리 프로토타입(`/api/v1/trips/{trip_id}/memorial/*`)은
당분간 유지하지만, 이 문서의 회원 단위 API가 정식 Memorial API입니다.

## 흐름

```text
클라이언트
  -> POST /api/v1/memorial/photos (사진 업로드)
  -> backend가 EXIF 촬영 시각/GPS 추출, 주소 역지오코딩, SQLite 저장
  -> GET /api/v1/memorial/calendar?year=...&month=... (사진 있는 날짜 달력 표시)
  -> GET /api/v1/memorial/days/{day} (촬영 시각 오름차순 = 발자국 순서)
  -> GET /api/v1/memorial/photos/{photo_id}/file (발자국 클릭 시 원본 표시)
```

## 공통 규칙

- API prefix: `/api/v1/memorial`
- 모든 엔드포인트는 `Authorization: Bearer <access_token>` 헤더가 필요합니다.
  토큰은 `GET /api/v1/auth/google/callback` 응답의 `access_token`이며 JWT
  `sub` 클레임이 `google_users.id`입니다. 인증 흐름 상세는
  [auth.md](./auth.md)를 봅니다.
- 날짜는 `YYYY-MM-DD`, 시각은 ISO 8601(`2026-07-01T10:30:00+09:00`) 형식입니다.
- 에러 응답 형식은 `{"detail": "..."}`입니다.

| 상태 | 원인 |
| --- | --- |
| 401 | 토큰 누락·만료·위조 |
| 404 | 리소스 없음 또는 다른 회원의 리소스 |
| 415 | 이미지가 아닌 파일 업로드 |
| 413 | 사진 파일이 10MiB를 초과함 |
| 422 | 요청 형식 오류(필드 검증 실패) |

응답의 사진 객체(`MemorialPhoto`)는 아래 형태입니다.

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

## 메타데이터 결정 규칙

`taken_at`, `latitude`, `longitude`는 아래 우선순위로 결정합니다.

| 우선순위 | 출처 | 비고 |
| --- | --- | --- |
| 1 | 업로드 폼 필드 | 클라이언트가 명시적으로 보낸 값 |
| 2 | 사진 EXIF | `DateTimeOriginal`(+`OffsetTimeOriginal`), GPS IFD |
| 3 | 기본값 | `taken_at`은 서버 수신 시각(UTC), 위경도는 `null` |

- EXIF를 읽을 수 없는 파일(스크린샷, 메신저로 받은 사진 등)도 업로드는
  성공합니다. 위치가 없는 사진은 지도 발자국에서 제외하고 목록에만 노출하는
  것을 권장합니다.
- 지원 포맷은 JPEG, PNG, WEBP, HEIC/HEIF입니다. 그 외 `image/*`도 저장은
  되지만 EXIF 추출은 보장하지 않으며, 이미지가 아닌 파일은 415로 거부합니다.
- 역지오코딩은 타깃 지역 오사카, 응답 언어 `ko` 기준입니다.
  `GOOGLE_MAPS_API_KEY`가 없거나 호출이 실패하면 `address: null`로 저장되고
  업로드는 정상 진행됩니다.

## 사진 업로드

`POST /api/v1/memorial/photos` (multipart/form-data)

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `file` | file | 예 | 이미지 파일 |
| `taken_at` | string(ISO 8601) | 아니오 | 촬영 시각 재정의 |
| `latitude` | number(-90~90) | 아니오 | 위도 재정의 |
| `longitude` | number(-180~180) | 아니오 | 경도 재정의 |
| `memo` | string | 아니오 | 메모 |

사진 파일은 최대 10MiB까지 업로드할 수 있으며, 서버는 파일을 제한된 크기의
청크로 읽습니다. Content-Type이 `image/*`여도 실제 이미지로 판독되지 않으면
`415 Unsupported Media Type`으로 거부합니다.

응답은 `201 Created`와 `MemorialPhoto`입니다. 유효한 이미지의 EXIF 추출에
실패해도 201로 성공하며 메타데이터 결정 규칙의 기본값이 적용됩니다.

## 캘린더 조회

`GET /api/v1/memorial/calendar?year=2026&month=7`

| 파라미터 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `year` | int(2000~2100) | 예 | 연도 |
| `month` | int(1~12) | 예 | 월 |

응답 `200 OK`는 사진이 1장 이상 있는 날짜만 날짜 오름차순으로 포함합니다.
프론트엔드는 이 목록으로 캘린더 화면을 그립니다.

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

## 날짜별 타임라인 조회

`GET /api/v1/memorial/days/{day}` (예: `/days/2026-07-01`)

응답 `200 OK`는 `taken_at` 오름차순으로 정렬되며, `seq`(0부터)가 지도 발자국
애니메이션 순서입니다. 사진이 없는 날짜는 `items: []`로 200 응답합니다.

```json
{
  "day": "2026-07-01",
  "items": [
    { "seq": 0, "photo": { "...MemorialPhoto (10:30 촬영)": "..." } },
    { "seq": 1, "photo": { "...MemorialPhoto (12:05 촬영)": "..." } }
  ]
}
```

## 사진 메타데이터 조회

`GET /api/v1/memorial/photos/{photo_id}`

응답은 `200 OK`와 `MemorialPhoto`입니다. 없거나 다른 회원의 사진이면
404입니다.

## 사진 원본 파일 조회

`GET /api/v1/memorial/photos/{photo_id}/file`

응답은 `200 OK`와 이미지 바이너리이며, `Content-Type`은 업로드 당시
타입입니다. 발자국 클릭 시 이 URL(`MemorialPhoto.file_url`)로 원본을
표시합니다.

## 사진 정보 수정

`PATCH /api/v1/memorial/photos/{photo_id}`

```json
{ "taken_at": "...", "latitude": 34.7, "longitude": 135.5, "memo": "..." }
```

모든 필드는 선택이며 보낸 필드만 수정됩니다. 위경도가 바뀌면 주소를 다시
조회합니다. 응답은 `200 OK`와 수정된 `MemorialPhoto`입니다.

## 사진 삭제

`DELETE /api/v1/memorial/photos/{photo_id}`

응답은 `204 No Content`이며 DB 레코드와 저장된 파일을 함께 삭제합니다.

## 환경 설정

| 환경 변수 | 기본값 | 설명 |
| --- | --- | --- |
| `GOOGLE_AUTH_DB_PATH` | `data/google_auth.db` | 사용자·사진 메타데이터 SQLite 경로 |
| `MEMORIAL_PHOTO_DIR` | `data/memorial_photos` | 사진 파일 저장 디렉터리 |
| `GOOGLE_MAPS_API_KEY` | 없음 | 역지오코딩 키, 없으면 `address: null` |

## 저장 위치

- 라우터: `src/chiwawa_backend/routers/memorial.py` (`album_router`)
- 사진 서비스: `src/chiwawa_backend/services/memorial_photos.py`
- EXIF 추출: `src/chiwawa_backend/services/exif.py`
- 역지오코딩: `src/chiwawa_backend/services/geocode.py`
- 테이블 스키마: `src/chiwawa_backend/sql/002_memorial_photos.sql`
  (`memorial_photos`, `user_id → google_users.id ON DELETE CASCADE`)
- 사진 파일: `data/memorial_photos/{user_id}/{uuid}.{ext}` (Git 제외)
