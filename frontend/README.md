# chiwawa Flutter Prototype

한국인 여행객을 위한 AI 여행 통합 플래너 앱 프로토타입입니다.

## 실행

```bash
flutter pub get
flutter run -d chrome
```

웹 서버로 바로 띄우려면:

```bash
flutter run -d web-server --web-hostname 127.0.0.1 --web-port 5190
```

## API base URL 설정

현재 앱은 mock/prototype이지만, 실제 FastAPI 서버를 붙일 때는 실행 대상에 따라 `API_BASE_URL`을 다르게 넘긴다.

```bash
# iOS 시뮬레이터 / macOS Chrome
flutter run -d chrome --dart-define=API_BASE_URL=http://127.0.0.1:8000
flutter run -d ios --dart-define=API_BASE_URL=http://127.0.0.1:8000

# Android 에뮬레이터
flutter run -d android --dart-define=API_BASE_URL=http://10.0.2.2:8000

# 실제 기기
flutter run -d <device-id> --dart-define=API_BASE_URL=http://<LAN-IP>:8000
```

Android 에뮬레이터에서 `127.0.0.1`은 개발 PC가 아니라 에뮬레이터 자기 자신을 가리키므로 `10.0.2.2`를 사용한다. 실제 기기는 백엔드 서버가 떠 있는 PC의 같은 네트워크 LAN IP를 사용한다.

iOS 시뮬레이터 실행은 macOS에 전체 Xcode와 CocoaPods가 설치된 뒤 가능합니다.

```bash
flutter pub get
flutter run -d ios
```

## 구현 범위

- 하단 탭 라우팅: 홈 / 일정 / 탐색 / 기록 / 마이
- Riverpod UI 상태: mock auth, 저장한 사진 장소, 일정 후보, AI 경로 결과, 사진 분석 결과
- 홈 일정 타임라인, 빈 시간 추천 바텀시트, 핵심 기능 바로가기
- AI 일정 설계: 장소 태그 추가/삭제, 사진으로 저장한 장소 반영, 경로 최적화 로딩, 결과 카드
- 사진 탐색: 업로드 영역, 이미지 선택, 분석 로딩, 결과 카드, 일정 후보 저장
- Memorial 여행 요약, 일자별 사진 그리드, 공유/내보내기 버튼
- 마이페이지 계정/설정 화면, Google OAuth + JWT 준비 로그인 화면, 게스트 둘러보기
- Pretendard 번들 폰트로 한글 UI 렌더링 안정화

## 문서

- [프론트엔드 기술 기능 명세서](docs/frontend-spec.md)

## 검증

```bash
flutter analyze
flutter test
flutter build web
```
