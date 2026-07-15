# Memorial API

## 범위

새 모바일 앱의 Memorial 원본은 휴대폰 로컬 저장소에 보관합니다. 백엔드는
`/api/v1/trips/{trip_id}/memorial/*`로 여행별 사진 메타데이터만 저장하고, 파일
경로나 원본 바이트를 받지 않습니다. S3와 백엔드 파일 저장소는 사용하지
않습니다. 지도 렌더링과 로컬 파일 접근은 앱 책임입니다.

`device_photo_id`는 앱 저장소에서 생성한 opaque 식별자이며 백엔드가 해석하거나
파일로 변환하지 않습니다. `storage` 응답은 항상 `device`입니다.

기존 `/api/v1/memorial/*` 회원 단위 파일 앨범은 레거시 호환용으로만 남아 있으며
새 앱 흐름에서는 사용하지 않습니다.

## 앱 사진 메타데이터 등록

`POST /api/v1/trips/{trip_id}/memorial/photos` (`application/json`)

```json
{
  "device_photo_id": "device-photo-001",
  "file_name": "IMG_0001.jpg",
  "taken_at": "2026-07-10T20:30:00+09:00",
  "latitude": 35.6595,
  "longitude": 139.7005,
  "memo": "Shibuya at night"
}
```

이 API는 사진 파일을 업로드하지 않습니다. `device_photo_id`, 파일명, 촬영 시각,
좌표, 메모만 SQLite 상태에 저장하며 응답에는 `storage: "device"`가 포함됩니다.
앱은 이 메타데이터와 응답 ID를 로컬 사진 레코드에 연결해 오프라인 캘린더와
타임라인을 렌더링합니다.

아래 회원 단위 파일 앨범 설명은 레거시 API의 동작을 설명합니다. 새 앱에서는
호출하지 않습니다.

## 레거시 회원 단위 파일 앨범

## 저장 구조

```text
SQLite memorial_photos row
  stored_path = {user_id}/{uuid}.{ext}
                  |
                  v
MEMORIAL_PHOTO_DIR/{user_id}/{uuid}.{ext}
```

- DB에는 설정 root가 아닌 사용자별 상대 경로를 저장합니다.
- root, 사용자 디렉터리, `.trash`, `.health`는 `0700`, 파일은 `0600`입니다.
- root는 이 서비스의 사진만 포함하는 전용 디렉터리여야 하며 SQLite DB를 root
  안에 둘 수 없습니다. 알 수 없는 기존 항목이 있으면 startup이 fail closed합니다.
- path traversal, symlink, FIFO/비정규 파일, 사용자 ID 불일치, 이름 충돌과
  overwrite를 거부합니다.
- 삭제는 로컬 `.trash` staging과 DB transaction을 결합합니다. commit 실패 시
  파일을 복구하고, process 중단 residue는 다음 startup에서 조정합니다.
- startup recovery는 DB orphan, 만료 upload lease, 중단된 delete를 정리하되
  진행 중인 upload 파일은 보존합니다.
- SQLite DB와 사진 root는 같은 시점에 함께 백업해야 합니다.

## 공통 응답

| 상태 | 원인 |
| --- | --- |
| 400 | 잘못되거나 모순된 HTTP body framing |
| 401 | 토큰 누락·만료·위조 또는 잘못된 subject |
| 404 | 사진 없음 또는 다른 사용자의 사진 |
| 413 | request/file 크기 또는 사용자 사진 수·총 byte quota 초과 |
| 415 | 지원하지 않거나 실제로 해석할 수 없는 이미지 |
| 422 | query/form/PATCH 필드 불변식 위반 |
| 429 | 시간당 upload rate 또는 사용자/전역 동시성 초과 |
| 500 | 예상하지 못한 내부 오류 |
| 507 | 예약 byte까지 고려한 로컬 디스크 watermark 부족 |

429는 `Retry-After`를 포함합니다. 오류 본문은 항상
`{"detail": "..."}`입니다. private 사진 metadata와 파일 응답에는
`Cache-Control: private, no-store`가 적용되고 모든 응답은
`X-Content-Type-Options: nosniff`를 포함합니다.

## 업로드

`POST /api/v1/memorial/photos` (`multipart/form-data`)

| 필드 | 타입 | 필수 | 규칙 |
| --- | --- | --- | --- |
| `file` | file | 예 | 실제 이미지 검증 |
| `taken_at` | ISO 8601 datetime | 아니오 | EXIF 시각보다 우선 |
| `latitude` | number | 아니오 | longitude와 함께 제공 |
| `longitude` | number | 아니오 | latitude와 함께 제공 |
| `memo` | string | 아니오 | 사용자 메모 |

지원 format은 AVIF, GIF, HEIC/HEIF, JPEG, PNG, WebP입니다. multipart의 선언
Content-Type을 신뢰하지 않고 Pillow가 감지한 MIME을 저장·응답합니다. 모든
animated frame을 decode하고 최대 dimension·총 pixel 한도 및 decompression bomb를
검사합니다.

기본 한도는 사진 10 MiB, multipart request 12 MiB, 사용자당 1,000장·2 GiB,
시간당 upload 시도 60회, 사용자 동시 2회·전역 동시 8회, 로컬 여유 공간
1 GiB입니다. 한도는 환경 변수로 조정할 수 있으며 quota와 lease는
`BEGIN IMMEDIATE` transaction으로 동시에 예약합니다.

인증과 SQLite 공용 요청 동시성 선점은 multipart parsing 전에 수행합니다.
따라서 무토큰 요청은 body를 읽지 않고 401을, 여러 worker의 동시성 한도를 넘은
요청은 body를 읽지 않고 429를 반환합니다. 이후 실제 파일 크기를 확인한 lease가
quota와 디스크 예약을 담당합니다.

## 메타데이터와 시간

`taken_at`, 좌표는 다음 순서로 결정합니다.

1. 업로드 form 값
2. EXIF `DateTimeOriginal`/`OffsetTimeOriginal`과 GPS
3. `taken_at`만 서버의 현재 `Asia/Tokyo` 시각, 좌표는 null

offset이 없는 시각은 `Asia/Tokyo`로 해석하고 offset이 있는 시각은 같은 instant의
Tokyo 시각으로 정규화합니다. DB에는 표시용 Tokyo 시각, UTC instant,
`local_date`를 함께 저장합니다. 타임라인은 문자열이 아니라 UTC instant로
정렬하고 같은 instant는 photo ID로 안정 정렬합니다.

좌표는 항상 둘 다 숫자이거나 둘 다 null입니다. 좌표가 있으면
`GOOGLE_MAPS_API_KEY`로 한국어 역지오코딩을 시도하며 키가 없거나 호출이
실패해도 사진 저장은 성공하고 address는 null입니다.

## 조회

- `GET /api/v1/memorial/calendar?year=2026&month=7`: Tokyo `local_date`
  기준으로 사진이 있는 날짜와 count를 반환합니다.
- `GET /api/v1/memorial/days/{day}`: UTC instant 순의 사진과 0-based
  `seq`를 반환합니다. 사진이 없으면 빈 `items`입니다.
- `GET /api/v1/memorial/photos/{photo_id}`: metadata 단건을 반환합니다.
- `GET /api/v1/memorial/photos/{photo_id}/file`: 감지된 실제
  `image/avif|gif|heic|heif|jpeg|png|webp` MIME과 바이너리를 반환합니다.

사진 객체는 다음 형태입니다.

```json
{
  "id": 12,
  "file_name": "IMG_0301.jpg",
  "content_type": "image/jpeg",
  "taken_at": "2026-07-01T10:30:00+09:00",
  "latitude": 34.6687,
  "longitude": 135.5031,
  "address": "일본 오사카부...",
  "memo": "도톤보리에서 점심",
  "file_url": "/api/v1/memorial/photos/12/file",
  "created_at": "2026-07-09T02:11:45+00:00"
}
```

## 수정과 삭제

`PATCH /api/v1/memorial/photos/{photo_id}`

보낸 필드만 변경합니다. 생략과 명시적 null을 구분합니다.

- `taken_at: null`은 422입니다.
- `memo: null`은 메모를 지웁니다.
- 좌표를 변경하거나 지울 때는 latitude와 longitude를 함께 보내야 합니다.
- 두 좌표를 모두 null로 보내면 좌표와 address를 지웁니다.
- 숫자 좌표로 변경하면 address를 다시 조회합니다.

`DELETE /api/v1/memorial/photos/{photo_id}`는 DB row와 로컬 파일을 함께
삭제하고 `204 No Content`를 반환합니다.

## 환경 변수

| 변수 | 기본값 |
| --- | --- |
| `MEMORIAL_PHOTO_DIR` | `data/memorial_photos` |
| `MAX_MULTIPART_BODY_BYTES` | `12582912` |
| `MAX_PHOTO_BYTES` | `10485760` |
| `MAX_PHOTOS_PER_USER` | `1000` |
| `MAX_PHOTO_BYTES_PER_USER` | `2147483648` |
| `MAX_UPLOADS_PER_USER_PER_HOUR` | `60` |
| `MAX_CONCURRENT_UPLOADS` | `8` |
| `MAX_CONCURRENT_UPLOADS_PER_USER` | `2` |
| `UPLOAD_LEASE_TTL_SECONDS` | `300` |
| `MAX_IMAGE_PIXELS` | `40000000` |
| `MAX_IMAGE_DIMENSION` | `16384` |
| `MIN_FREE_DISK_BYTES` | `1073741824` |

운영의 `MEMORIAL_PHOTO_DIR`는 절대 경로이자 사진 전용 디렉터리여야 하며 같은
호스트의 일반 로컬 filesystem이어야 합니다. filesystem root, 다른 파일이 있는
공용 디렉터리, `DATABASE_PATH`를 포함하는 디렉터리는 거부합니다.
