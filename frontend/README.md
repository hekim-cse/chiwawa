# 치와와 — Frontend (Flutter)

AI와 함께하는 일본 여행 플래너 **치와와**의 클라이언트 애플리케이션입니다.
사진 기반 장소 탐색, AI 경로 최적화, 빈 시간대 추천, 여행 회고(Memorial)를
하나의 앱에서 제공하는 것을 목표로 합니다.

## 실행 방법

```bash
cd frontend
flutter pub get
flutter run          # 연결된 기기/시뮬레이터에서 실행
flutter run -d chrome  # 웹으로 실행
```

## 프로젝트 구조

```
lib/
├── app/               # 라우터(go_router), 테마
├── core/              # 목데이터, 인증, 사진 장소 저장
├── shared/widgets/    # 하단 네비게이션, 마스코트 아바타, 바텀시트 베이스
└── features/
    ├── auth/          # 로그인
    ├── home/          # 홈 — 오늘 일정 타임라인, 날씨 배너, 일정 카드
    ├── plan/          # 경로 계획 — 장소 입력, 경로 결과
    ├── explore/       # 사진 업로드 기반 장소 탐색
    ├── assist/        # 빈 시간 추천·일정 변경 바텀시트
    ├── memorial/      # 여행 회고 — 일자별 기록, 여행 요약
    └── mypage/        # 마이페이지
```

## 기술 스택

| 영역 | 사용 기술 |
|------|----------|
| 프레임워크 | Flutter (Dart) |
| 상태 관리 | flutter_riverpod |
| 라우팅 | go_router |
| HTTP | dio |
| 이미지 | image_picker, cached_network_image |
| 폰트 | Pretendard |

## 현재 상태

- 도쿄 3박 4일 목데이터 기반 화면 플로우 구현
- `flutter analyze` 통과 (오류 0건)
- 백엔드 API 연동 전 단계 (mock_data.dart 사용)
