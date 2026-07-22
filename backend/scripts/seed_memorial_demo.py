"""메모리얼 시연 데이터 주입 스크립트 (데모 전용).

백엔드 컨테이너 안에서 실행한다. 데모 유저를 만들고(google_users),
색상+날짜 라벨이 있는 이미지를 여러 장 생성해 메모리얼 사진으로 저장한다.

실행 (EC2에서):
    docker cp seed_memorial_demo.py chiwawa:/tmp/seed_memorial_demo.py
    docker exec chiwawa python /tmp/seed_memorial_demo.py

주의: 이 스크립트는 컨테이너의 환경변수(GOOGLE_AUTH_DB_PATH, MEMORIAL_PHOTO_DIR)를
그대로 사용하므로, EBS 볼륨(/data)에 데이터가 쌓인다.
"""

from __future__ import annotations

import datetime as dt
import io

from PIL import Image, ImageDraw

from chiwawa_backend.schemas.auth import GoogleUserProfile
from chiwawa_backend.services import memorial_photos
from chiwawa_backend.services.auth import save_or_update_user
from chiwawa_backend.services.memorial_photos import PhotoUpload

# 데모 유저 (google_sub로 upsert; 신선한 DB면 id=1이 되어 기본 설정과 일치)
DEMO_SUB = "demo-user"
DEMO_EMAIL = "demo@chiwawa.app"
DEMO_NAME = "데모 여행자"

# 오사카 도톤보리 인근 좌표 (paw map 표시용, 조금씩 흩뿌림)
OSAKA_LAT = 34.668736
OSAKA_LNG = 135.503111

# (파일명, 라벨, 촬영일시, 위도오프셋, 경도오프셋)
PHOTOS = [
    ("dotonbori.png", "도톤보리", dt.datetime(2026, 7, 20, 19, 30), 0.000, 0.000),
    ("glico.png", "글리코 사인", dt.datetime(2026, 7, 20, 20, 10), 0.001, 0.001),
    ("osaka_castle.png", "오사카성", dt.datetime(2026, 7, 21, 10, 0), 0.020, 0.015),
    ("shinsekai.png", "신세카이", dt.datetime(2026, 7, 21, 13, 30), -0.010, 0.008),
    ("umeda.png", "우메다 스카이", dt.datetime(2026, 7, 22, 11, 0), 0.030, -0.010),
    ("namba.png", "난바 거리", dt.datetime(2026, 7, 22, 18, 0), -0.002, 0.002),
]

COLORS = [
    (244, 143, 177),
    (129, 199, 132),
    (100, 181, 246),
    (255, 183, 77),
    (149, 117, 205),
    (77, 208, 225),
]


def _make_image(label: str, color: tuple[int, int, int]) -> bytes:
    image = Image.new("RGB", (960, 720), color=color)
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 40, 920, 680), outline=(255, 255, 255), width=6)
    draw.text((80, 320), f"CHIWAWA DEMO\n{label}", fill=(255, 255, 255))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def main() -> None:
    user = save_or_update_user(
        GoogleUserProfile(
            sub=DEMO_SUB,
            email=DEMO_EMAIL,
            name=DEMO_NAME,
            picture=None,
        ),
    )
    user_id = int(user.id)
    print(f"[seed] 데모 유저 준비 완료: id={user_id}, email={DEMO_EMAIL}")
    if user_id != 1:
        print(
            f"[seed] ⚠️ 데모 유저 id가 1이 아니에요({user_id}). "
            f"백엔드 컨테이너 환경변수에 MEMORIAL_DEMO_USER_ID={user_id} 를 넣고 재시작하세요.",
        )

    for index, (file_name, label, taken_at, d_lat, d_lng) in enumerate(PHOTOS):
        data = _make_image(label, COLORS[index % len(COLORS)])
        upload = PhotoUpload(
            file_name=file_name,
            content_type="image/png",
            data=data,
            taken_at=taken_at,
            latitude=OSAKA_LAT + d_lat,
            longitude=OSAKA_LNG + d_lng,
            memo=label,
        )
        saved = memorial_photos.save_photo(user_id, upload)
        print(f"[seed]  + {file_name} ({label}) taken_at={taken_at} id={saved.id}")

    print(f"[seed] 완료: 사진 {len(PHOTOS)}장 주입됨 (user_id={user_id})")


if __name__ == "__main__":
    main()
