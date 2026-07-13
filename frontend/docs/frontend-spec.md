# chiwawa 프론트엔드 기술 기능 명세서

## 1. 프로젝트 개요

chiwawa는 일본 자유여행을 준비하는 사용자가 사진 속 장소를 찾고, 해당 장소를 일정 후보로 저장한 뒤, AI 동선 최적화를 통해 여행 계획을 구성하고, 여행 후에는 사진과 방문 흐름을 기록으로 정리하는 AI 여행 플래너 서비스다.

프론트엔드 MVP는 Flutter 기반 App + Web 프로토타입으로 구현한다. 현재 단계에서는 실제 AI 분석, 실제 지도, 실제 DB 저장을 연결하지 않고 mock 상태와 mock 데이터를 사용한다. 인증은 Google OAuth + JWT 계약에 맞춰 화면, Repository, 토큰 저장 골격을 준비하되, 실서버 로그인은 OAuth code 수신 방식 합의 이후 연결한다.

### 핵심 사용자 흐름

1. 사용자가 사진 탐색 화면에서 여행지 사진을 업로드한다.
2. 앱이 사진 속 장소를 분석한 것처럼 mock 결과를 보여준다.
3. 사용자가 장소를 일정 후보에 저장한다.
4. 일정 설계 화면에서 저장된 장소를 일정 후보로 추가한다.
5. 사용자가 직접 입력한 장소와 사진으로 저장한 장소를 함께 AI 경로 최적화한다.
6. 여행 후 기록 화면에서 날짜별 방문 장소와 사진 흐름을 확인한다.

### MVP 포함 범위

- 홈에서 현재 여행과 오늘 일정 요약 표시
- 사진 기반 장소 탐색 mock 흐름
- 사진 탐색 결과를 일정 후보로 저장
- AI 일정 설계 장소 입력, 삭제, 저장 장소 불러오기
- AI 경로 최적화 mock 로딩과 결과 표시
- 여행 기록 요약과 날짜별 사진 grid 표시
- 마이페이지의 프로필, 계정 설정, 여행 관리 진입점
- Google OAuth 준비 로그인 화면과 게스트 둘러보기
- 모바일 중심 반응형 UI와 웹 직접 진입 경로

### MVP 제외 범위

- 실제 AI 이미지 분석
- 실제 지도/교통 API
- 실서버 OAuth code 수신 방식 확정 전 실제 Google 로그인 완료 플로우
- 실제 사진 메타데이터 분석
- 다크 모드

## 2. 기술 스택 및 선정 이유

### Flutter / Dart

Flutter는 하나의 코드베이스로 모바일 앱과 웹 프로토타입을 함께 만들 수 있어 App + Web 서비스 방향에 적합하다. 현재 프로젝트는 발표 시연에서 모바일 앱처럼 보이는 화면과 브라우저 직접 확인이 모두 필요하므로 Flutter Web 지원이 유리하다.

카드, 하단 탭, 바텀시트, chip, 입력 폼, 사진 업로드 영역 같은 UI를 빠르게 구성할 수 있고, Material 3 위젯을 기반으로 안정적인 인터랙션을 만들 수 있다. Dart의 정적 타입은 mock 데이터에서 DTO 구조로 확장할 때 필드 누락이나 타입 오류를 줄이는 데 도움이 된다.

현재 사용 위치:

- `lib/main.dart`: 앱 진입점
- `lib/app/router.dart`: 라우팅
- `lib/app/theme.dart`: 공통 테마
- `lib/features/*`: 기능별 화면

백엔드 연결 시 확장 방향:

- 화면별 mock 데이터를 DTO model로 치환
- Riverpod provider에서 Repository를 호출
- API 응답에 따라 loading, success, error, empty 상태 표현

### Riverpod

Riverpod은 화면 간 공유되는 상태를 가볍고 명시적으로 관리하기 위해 사용한다. chiwawa의 MVP에는 인증 상태, 사진으로 저장한 장소, 일정 후보 목록, AI 최적화 로딩 상태처럼 여러 화면을 오가는 상태가 있다.

Provider override가 쉬워 위젯 테스트에서 특정 상태를 주입하기 좋다. 예를 들어 사진 분석 결과가 보이는 상태, 로그인된 상태, 저장 장소가 존재하는 상태를 각각 독립적으로 검증할 수 있다.

현재 사용 위치:

- `authControllerProvider`: signedOut / guest / signedIn 인증 상태
- `authTokenProvider`: Dio interceptor가 참조하는 JWT
- `savedPhotoPlacesProvider`: 사진 탐색에서 저장한 장소 목록
- `selectedPlacesProvider`: 일정 설계 후보 장소
- `routeOptimizationProvider`: 경로 최적화 작업 상태와 결과
- `confirmedRouteProvider`: 확정한 최적 경로

백엔드 연결 시 확장 방향:

- 단순 `StateProvider`를 `AsyncNotifierProvider` 또는 `FutureProvider`로 확장
- API 호출 결과를 `AsyncValue`로 관리
- 화면은 Repository가 아닌 provider만 바라보도록 유지

### go_router

go_router는 선언형 라우팅과 웹 URL 직접 진입을 지원한다. 현재 앱은 하단 탭이 필요한 주요 화면과 하단 탭이 없어야 하는 인증 화면이 구분되어야 하므로 `ShellRoute` 구조가 적합하다.

현재 라우트:

| 경로 | 화면 | 하단 탭 | 역할 |
| --- | --- | --- | --- |
| `/home` | HomeScreen | 표시 | 현재 여행과 오늘 일정 요약 |
| `/plan` | PlanScreen | 표시 | AI 일정 설계 |
| `/explore` | ExploreScreen | 표시 | 사진 기반 장소 탐색 |
| `/memorial` | MemorialScreen | 표시 | 여행 기록 정리 |
| `/mypage` | MyPageScreen | 표시 | 프로필, 설정, 여행 관리 |
| `/auth` | AuthScreen | 숨김 | Google 로그인 / 게스트 진입 |

백엔드 연결 시 확장 방향:

- 로그인/게스트 선택 전에는 redirect에서 `/auth`로 보호
- 상세 화면이 생기면 `/trips/:tripId`, `/trips/:tripId/days/:dayId` 형태로 확장
- 웹 시연 URL을 고정해 QA와 발표 흐름을 안정화

### Dio

Dio는 FastAPI 백엔드와 JSON 통신을 구성하기 쉽고, 이미지 업로드를 위한 multipart 요청, 인증 토큰 interceptor, 공통 에러 처리를 구성하기 적합하다.

백엔드 연결 시 확장 방향:

- `DioClient`: baseUrl, timeout, headers, interceptors 관리
- `AuthRepository`: Google OAuth code 교환, `/auth/me` 프로필 API 호출
- `TripRepository`: 여행/일정 API 호출
- `PhotoPlaceRepository`: 이미지 분석/저장 장소 API 호출
- `PlanRepository`: 경로 최적화 API 호출
- `MemorialRepository`: 여행 기록 API 호출

### image_picker

image_picker는 사진 기반 장소 탐색의 핵심 입력인 갤러리 선택과 카메라 촬영 흐름을 제공한다. MVP에서는 선택한 이미지 경로를 화면에 표시하고, 일정 시간 후 mock 분석 결과를 보여준다.

백엔드 연결 시 확장 방향:

- 선택한 이미지 파일을 multipart로 업로드
- 업로드 진행 상태를 loading UI로 표현
- 분석 실패, 파일 선택 취소, 권한 거부 상태를 분리해 안내

### intl

intl은 여행 기간, 날짜별 기록, 일정 시간, 현지 시간 표기 확장을 위해 유지한다. 현재 MVP는 문자열 mock 데이터를 사용하지만, 서버 응답이 ISO date/time으로 들어오면 한국어 날짜 포맷으로 변환해야 한다.

백엔드 연결 시 확장 방향:

- 여행 기간 표시
- 일정 시작/종료 시간 표시
- 날짜별 기록 헤더 표시
- 현지 시간대 표기

### Material 3 + 커스텀 테마

Material 3는 NavigationBar, BottomSheet, FilledButton, OutlinedButton, Chip, TextField 같은 기본 컴포넌트를 안정적으로 제공한다. chiwawa는 기본 Material 스타일 위에 핑크 브랜드 톤, Pretendard 폰트, 카드 테두리와 그림자 스타일을 입혀 일관된 화면을 구성한다.

현재 테마 기준:

- 브랜드명: `chiwawa`
- 주요 한글 타이틀: `치와와`
- primary: `#E45F78`
- background: `#FFF9FA`
- fontFamily: `Pretendard`
- 모바일 최대 콘텐츠 폭: `430`

### 이미지 리소스 관리

Flutter 화면에서 사용하는 이미지는 `assets/images/` 아래에 모아 관리한다. 마스코트는 `assets/images/mascot/chiwawa_mascot.png`, 목데이터 이미지는 `assets/images/mock/` 아래 파일을 사용한다. 화면에서는 동일 이미지를 크기별로 복제하지 않고 `SizedBox`, `AspectRatio`, `BoxFit`, `ClipRRect` 같은 위젯으로 크기와 표시 방식을 조절한다.

이미지 경로는 화면에 직접 문자열로 쓰지 않고 `AppImages`, `MockImages` 상수를 통해 참조한다. `pubspec.yaml`은 `assets/images/` 디렉터리 기준으로 등록한다.

iOS `Assets.xcassets`, Android `mipmap-*`, Web `icons/*`와 `favicon.png`는 플랫폼 앱 아이콘/PWA 구조이므로 기존 위치를 유지한다. React/Vite prototype용 `public/assets` 이미지는 Flutter 앱 리소스와 별도로 취급한다.

## 3. 화면 IA 및 라우팅 명세

### 하단 탭 구조

하단 탭은 사용자가 핵심 기능을 빠르게 오갈 수 있도록 5개로 고정한다.

| 탭 | 경로 | 목적 |
| --- | --- | --- |
| 홈 | `/home` | 현재 여행 현황 확인 |
| 일정 | `/plan` | AI 일정 설계 |
| 탐색 | `/explore` | 사진 기반 장소 탐색 |
| 기록 | `/memorial` | 여행 기록 정리 |
| 마이 | `/mypage` | 계정, 설정, 여행 관리 |

`/auth`는 하단 탭 밖에 둔다. Google 로그인과 게스트 진입 선택은 현재 작업 맥락을 잠시 벗어나는 독립 화면이므로 하단 탭이 보이면 사용자가 인증 흐름에서 이탈하기 쉽다.

### 공통 레이아웃 규칙

- 모바일 기준 콘텐츠 최대 폭은 `430`으로 제한한다.
- 데스크톱 브라우저에서는 모바일 화면이 중앙 정렬되어야 한다.
- 주요 화면은 `SafeArea` 안에서 표시한다.
- 하단 탭이 있는 화면은 bottom padding을 충분히 두어 탭과 콘텐츠가 겹치지 않게 한다.
- 버튼과 카드 텍스트는 모바일 폭에서 줄바꿈 또는 ellipsis로 처리한다.
- 실제 기능이 없는 액션은 아무 반응 없이 두지 않고 스낵바로 준비 중 상태를 알린다.

## 4. 화면별 기능 명세

### 홈 `/home`

목적:

- 사용자가 앱을 열었을 때 현재 여행 상태와 오늘의 흐름을 빠르게 파악한다.
- 핵심 기능인 일정 설계와 사진 탐색으로 이동할 수 있는 진입점을 제공한다.

표시 데이터:

- 여행명
- 도시
- 날씨
- 현재 여행 일차
- 오늘 일정 목록
- 일정별 시간, 장소, 이동수단, 상태

사용자 액션:

- `AI 일정 설계` 진입
- `사진으로 장소 찾기` 진입
- 빈 시간 추천 바텀시트 열기
- 준비 중 액션 선택 시 스낵바 표시

상태:

- 현재는 `mock_data.dart`의 `tripInfo`, `schedules`를 사용한다.
- 백엔드 연결 후 현재 여행 조회 API와 날짜별 일정 조회 API로 대체한다.

수용 기준:

- 홈 진입 시 브랜드, 현재 여행명, 오늘 일정이 표시된다.
- 하단 탭에서 `홈`이 선택 상태로 보인다.
- 모바일 폭에서 일정 카드 텍스트가 겹치지 않는다.

### 사진 탐색 `/explore`

목적:

- 사용자가 사진 속 장소를 찾고, 찾은 장소를 일정 설계 후보로 저장한다.

표시 데이터:

- 사진 업로드 영역
- 분석 로딩 상태
- 장소 분석 결과
- 최근 탐색 목록
- 지도 placeholder

사용자 액션:

- 사진 업로드 영역 탭
- 갤러리 또는 카메라 선택
- 이미지 선택 후 분석 mock 실행
- 최근 탐색 카드 탭
- 결과 장소를 일정 후보에 저장
- 경로 안내 버튼 탭

상태:

- `exploreImagePathProvider`: 선택 이미지 경로
- `exploreAnalyzingProvider`: 분석 로딩 여부
- `exploreResultVisibleProvider`: 결과 카드 표시 여부
- `exploreSelectedResultProvider`: 현재 표시할 분석 결과
- `savedPhotoPlacesProvider`: 일정 후보로 저장한 장소

수용 기준:

- 사진 선택 후 로딩이 보이고 결과 카드가 표시된다.
- `일정에 추가` 클릭 시 저장 성공 스낵바가 표시된다.
- 같은 장소를 다시 저장하면 중복 안내 스낵바가 표시된다.
- 저장된 결과 카드에는 `일정 후보 저장됨` 상태가 표시된다.
- 저장한 장소는 일정 설계 화면에서 확인할 수 있다.

백엔드 연결 후 변경:

- 이미지 선택 후 multipart 업로드 API 호출
- 서버가 반환한 후보 장소 목록을 카드로 표시
- 장소명뿐 아니라 장소 id, 좌표, 신뢰도를 함께 저장

### AI 일정 설계 `/plan`

목적:

- 직접 입력한 장소와 사진 탐색에서 저장한 장소를 일정 후보로 모아 최적 방문 순서를 추천한다.

표시 데이터:

- 장소 입력 필드
- 선택된 장소 chip 목록
- 사진으로 저장한 장소 목록
- AI 경로 최적화 버튼
- 최적 경로 결과 카드
- 확정 버튼

사용자 액션:

- 장소명 직접 입력
- 장소 chip 삭제
- 사진으로 저장한 장소 chip 선택
- 사진으로 저장한 장소 chip 삭제
- AI 경로 최적화 실행
- 최적화 결과 확인
- 일정 확정 버튼 클릭

상태:

- `selectedPlacesProvider`: 일정 후보 장소 목록
- `savedPhotoPlacesProvider`: 사진 탐색에서 저장된 장소
- `routeOptimizationProvider`: 최적화 작업 상태와 결과
- `confirmedRouteProvider`: 확정한 최적 경로

수용 기준:

- 후보 장소가 2개 미만이면 최적화 버튼이 비활성화된다.
- 후보 장소가 2개 이상이면 최적화 버튼이 활성화된다.
- 최적화 실행 중 로딩 상태가 표시된다.
- 최적화 완료 후 순서가 있는 경로 결과가 표시된다.
- 사진 저장 장소를 선택하면 일정 후보 chip에 반영된다.
- 사진 저장 장소는 일정 설계 화면에서 삭제할 수 있다.
- `이 일정으로 확정하기` 클릭 시 Memorial 화면의 확정 일정 preview에 반영된다.

백엔드 연결 후 변경:

- 후보 장소는 문자열이 아니라 장소 id와 좌표를 포함한 객체로 관리한다.
- 최적화 API 요청에는 tripId, 날짜, 후보 장소 목록, 이동수단 옵션을 포함한다.
- 최적화 결과는 서버 응답의 방문 순서와 이동 시간으로 표시한다.

### 여행 기록 `/memorial`

목적:

- 여행 후 사진과 방문 장소를 날짜별로 정리해 사용자가 여행 흐름을 회고할 수 있게 한다.

표시 데이터:

- 여행명
- 여행 기간
- 총 여행 일수
- 방문 장소 수
- 이동 거리
- 날짜별 방문 장소
- 날짜별 사진 grid
- AI 일정 설계에서 확정한 일정 preview

사용자 액션:

- 날짜별 기록 확인
- 공유하기 버튼 클릭
- 앨범 내보내기 버튼 클릭

상태:

- 현재는 `memorialSummary`, `memorialDays` mock 데이터를 사용한다.
- 공유하기와 앨범 내보내기는 mock 버튼으로 유지한다.

수용 기준:

- 여행 요약 카드가 표시된다.
- 날짜별 장소 chip과 사진 grid가 표시된다.
- 이미지 로딩 실패 시 UI가 깨지지 않도록 placeholder 확장이 필요하다.

백엔드 연결 후 변경:

- 여행 기록 요약 API에서 통계 데이터를 받는다.
- 날짜별 기록 API에서 방문 장소와 사진 URL을 받는다.
- 사진 메타데이터 분석은 백엔드에서 처리하고 프론트는 결과만 표시한다.

### 마이 `/mypage`

목적:

- 사용자가 프로필, 계정 상태, 앱 설정, 여행 관리 진입점을 한 화면에서 확인한다.

표시 데이터:

- 마스코트 아바타
- 닉네임
- 현재 여행 상태
- 서비스 설명
- 내 여행 관리 메뉴
- 계정 및 앱 설정 메뉴
- 도움말 메뉴

사용자 액션:

- 현재 여행 일정으로 이동
- AI 일정 설계로 이동
- 사진으로 장소 찾기로 이동
- 여행 기록으로 이동
- 계정 연결 화면으로 이동
- 준비 중 설정 클릭 시 스낵바 표시

상태:

- `authControllerProvider`에서 이름, 이메일, 로그인/게스트 상태를 읽는다.
- 게스트 상태에서는 `로그인 없이 둘러보는 중`을 표시한다.
- 로그인 후에는 이메일 연결 상태를 표시한다.

수용 기준:

- 로그인 전 기본 닉네임은 `치와와 여행자`다.
- Google 로그인 후 사용자 이름/이메일이 프로필 카드에 반영된다.
- 계정 연결 row를 누르면 `/auth`로 이동한다.
- 로그인 상태에서는 로그아웃 row가 표시된다.
- 하단 탭에서 `마이`가 선택 상태로 보인다.

### 인증 `/auth`

목적:

- Google OAuth 로그인 진입점과 로그인 없이 둘러보기 선택지를 제공한다.
- Mock 모드에서는 백엔드 없이도 Google 로그인 성공 상태를 재현한다.

표시 데이터:

- chiwawa 브랜드
- 마스코트
- Google로 시작하기 버튼
- 로그인 없이 둘러보기 버튼

사용자 액션:

- Google 로그인 시작
- 로그인 없이 둘러보기
- 뒤로가기

상태:

- `authControllerProvider`가 `signedOut / guest / signedIn` 3상태를 관리한다.
- signedIn 상태에서는 `shared_preferences`에 JWT와 사용자 표시 정보를 저장한다.
- Dio 요청은 `authTokenProvider`의 토큰을 `Authorization: Bearer` 헤더로 첨부한다.

수용 기준:

- 첫 진입 시 `/auth`가 표시된다.
- 로그인 없이 둘러보기를 누르면 `/home`으로 이동한다.
- Mock 모드에서 Google로 시작하기를 누르면 홈으로 이동하고 마이페이지에 계정 연결 상태가 반영된다.
- API 모드에서는 `/api/v1/auth/google/login`으로 이동한다.
- OAuth `code`를 수신하면 `/api/v1/auth/google/callback?code=...`으로 `access_token`을 교환한다.
- `/auth`에서는 하단 탭이 보이지 않는다.

## 5. 상태 관리 명세

### 현재 Provider 목록

| Provider | 타입 | 역할 | 사용 화면 |
| --- | --- | --- | --- |
| `authControllerProvider` | `StateNotifierProvider` | 인증 상태와 사용자 정보 | `/auth`, `/mypage`, router |
| `authTokenProvider` | `StateProvider<String?>` | API 요청 Authorization 토큰 | Dio interceptor |
| `savedPhotoPlacesProvider` | `StateNotifierProvider` | 사진으로 저장한 장소 목록 | `/explore`, `/plan` |
| `selectedPlacesProvider` | `StateProvider<List<String>>` | 일정 후보 장소 목록 | `/plan` |
| `routeOptimizationProvider` | `StateProvider<RouteOptimizationState>` | 경로 최적화 작업 상태와 결과 | `/plan` |
| `confirmedRouteProvider` | `StateNotifierProvider` | 사용자가 확정한 최적 경로 | `/plan`, `/memorial` |
| `exploreImagePathProvider` | `StateProvider<String?>` | 선택 이미지 경로 | `/explore` |
| `exploreAnalyzingProvider` | `StateProvider<bool>` | 사진 분석 로딩 | `/explore` |
| `exploreResultVisibleProvider` | `StateProvider<bool>` | 분석 결과 표시 여부 | `/explore` |
| `exploreSelectedResultProvider` | `StateProvider<PhotoSearchResult>` | 현재 분석 결과 | `/explore` |

### 핵심 데이터 흐름

사진 탐색에서 일정 설계로 이어지는 흐름:

1. `/explore`에서 사용자가 사진을 선택한다.
2. `exploreAnalyzingProvider`가 true가 되어 로딩을 표시한다.
3. mock 분석 완료 후 `exploreSelectedResultProvider`가 결과를 가진다.
4. 사용자가 `일정에 추가`를 누른다.
5. `savedPhotoPlacesProvider.addPlace()`가 호출된다.
6. `/plan`은 `savedPhotoPlacesProvider`를 watch한다.
7. 저장 장소가 있으면 `사진으로 저장한 장소` 섹션을 표시한다.
8. 사용자가 저장 장소 chip을 누르면 `selectedPlacesProvider`에 추가된다.
9. 후보 장소가 2개 이상이면 AI 경로 최적화가 가능해진다.
10. 최적화 결과를 확정하면 `confirmedRouteProvider.confirm()`이 호출된다.
11. `/memorial`은 `confirmedRouteProvider`를 watch해 확정 일정 preview를 표시한다.

인증에서 마이페이지로 이어지는 흐름:

1. `/mypage`에서 `계정 연결` row를 누른다.
2. `/auth`로 이동한다.
3. 사용자가 Google로 시작하기 또는 로그인 없이 둘러보기를 선택한다.
4. Mock 모드에서는 `authControllerProvider.signInWithToken()` 또는 `continueAsGuest()`가 호출된다.
5. API 모드에서는 OAuth `code` 수신 후 callback API로 `access_token`을 교환한다.
6. 프로필 카드와 계정 연결 설명에 이름/이메일 또는 게스트 상태가 반영된다.

### 백엔드 연결 후 상태 전환 기준

| 현재 상태 | 백엔드 연결 후 |
| --- | --- |
| `AuthState` | Google OAuth + JWT 세션, `UserProfileDto` |
| `PhotoSearchResult` | `PhotoPlaceDto`, `PlaceCandidateDto` |
| `List<PhotoSearchResult>` | 서버 저장 장소 목록 |
| `List<String>` 일정 후보 | `List<PlanCandidatePlace>` |
| `bool` 로딩 상태 | `AsyncValue<T>` |
| 고정 mock 결과 | Repository API 응답 |

## 6. 백엔드 연동 구상

### 프론트 API 레이어 구조

백엔드 연결 시 화면에서 직접 Dio를 호출하지 않는다. API 호출은 feature별 Repository가 담당하고, 화면은 Riverpod provider를 통해 상태만 구독한다.

권장 구조:

```text
lib/
  core/
    api/
      dio_client.dart
      api_exception.dart
    models/
      common_response.dart
  features/
    auth/
      data/auth_repository.dart
      data/auth_dto.dart
    trips/
      data/trip_repository.dart
      data/trip_dto.dart
    explore/
      data/photo_place_repository.dart
      data/photo_place_dto.dart
    plan/
      data/plan_repository.dart
      data/plan_dto.dart
    memorial/
      data/memorial_repository.dart
      data/memorial_dto.dart
```

공통 원칙:

- baseUrl은 환경별로 분리한다.
- access token은 interceptor에서 자동 첨부한다.
- API 에러는 `ApiException`으로 변환한다.
- 화면은 실패 메시지를 스낵바 또는 inline error로 보여준다.
- 목록이 비어 있으면 empty state를 표시한다.
- mock 데이터와 API 데이터의 필드명을 최대한 맞춰 교체 비용을 줄인다.

### 인증/계정 API

필요 API:

| 기능 | Method | Endpoint 초안 | 요청 | 응답 |
| --- | --- | --- | --- | --- |
| Google 로그인 시작 | GET | `/api/v1/auth/google/login` | 없음 | 302 Google OAuth redirect |
| OAuth code 교환 | GET | `/api/v1/auth/google/callback?code=...` | code, state? | `{ user, access_token }` |
| 내 정보 조회 | GET | `/api/v1/auth/me` | Bearer token | `{ sub, email, name }` |
| 로그아웃 | client | local only | 없음 | 토큰 삭제 |

프론트 필요 데이터:

```json
{
  "access_token": "string",
  "user": {
    "id": "string",
    "google_sub": "string",
    "email": "user@example.com",
    "name": "치와와 여행자",
    "picture": "https://lh3.googleusercontent.com/..."
  }
}
```

연결 화면:

- `/auth`: Google 로그인, 게스트 진입
- `/mypage`: 프로필 카드, 계정 연결 상태

MVP 대체 지점:

- Mock Google 로그인은 `mock-jwt-token`과 mock 사용자 정보로 처리한다.
- API 모드에서는 저장된 token이 있으면 `/api/v1/auth/me`로 프로필을 복구한다.
- OAuth code 수신은 `/auth?code=...` 웹 리다이렉트와 `chiwawa://auth?code=...` 앱 딥링크를 모두 처리할 수 있게 둔다.

### 현재 여행/일정 API

필요 API:

| 기능 | Method | Endpoint 초안 | 요청 | 응답 |
| --- | --- | --- | --- | --- |
| 현재 여행 조회 | GET | `/trips/current` | 없음 | trip |
| 여행 생성 | POST | `/trips` | city, period, members | trip |
| 날짜별 일정 조회 | GET | `/trips/{tripId}/days/{date}/schedules` | 없음 | schedules |
| 일정 확정 저장 | POST | `/trips/{tripId}/schedules` | optimizedRoute | schedule |

프론트 필요 데이터:

```json
{
  "tripId": "string",
  "tripName": "도쿄 봄 여행",
  "city": "도쿄, 일본",
  "period": {
    "startDate": "2025-04-01",
    "endDate": "2025-04-04"
  },
  "currentDay": 3,
  "members": 2,
  "weatherSummary": "18°C 맑음"
}
```

일정 항목 데이터:

```json
{
  "id": "string",
  "startTime": "09:00",
  "endTime": "10:30",
  "placeName": "아사쿠사 센소지",
  "transport": "도보",
  "status": "ongoing"
}
```

연결 화면:

- `/home`: 현재 여행, 오늘 일정
- `/plan`: 일정 확정 저장
- `/mypage`: 현재 여행 상태

MVP 대체 지점:

- `tripInfo`, `schedules` mock 데이터를 `TripRepository` 응답으로 교체한다.

### 사진 기반 장소 탐색 API

필요 API:

| 기능 | Method | Endpoint 초안 | 요청 | 응답 |
| --- | --- | --- | --- | --- |
| 사진 장소 분석 | POST | `/photo-places/analyze` | multipart image | candidates |
| 분석 결과 상세 조회 | GET | `/photo-places/analyses/{analysisId}` | 없음 | analysis |

요청:

- `multipart/form-data`
- field: `image`
- 선택 확장 field: `tripId`, `cityHint`, `currentLat`, `currentLng`

응답 데이터:

```json
{
  "analysisId": "string",
  "candidates": [
    {
      "placeId": "string",
      "name": "아사쿠사 센소지",
      "address": "도쿄 다이토구 아사쿠사 2-3-1",
      "category": "사찰·관광지",
      "latitude": 35.7148,
      "longitude": 139.7967,
      "confidence": 0.92,
      "imageUrl": "https://example.com/photo.jpg"
    }
  ]
}
```

연결 화면:

- `/explore`

MVP 대체 지점:

- `photoSearchResult` 고정 mock 결과를 서버 candidate 목록으로 교체한다.
- 결과 카드에서 신뢰도와 후보 복수 선택 UI를 추가할 수 있다.

### 사진 저장 장소 API

필요 API:

| 기능 | Method | Endpoint 초안 | 요청 | 응답 |
| --- | --- | --- | --- | --- |
| 저장 장소 목록 | GET | `/trips/{tripId}/saved-photo-places` | 없음 | savedPlaces |
| 장소 저장 | POST | `/trips/{tripId}/saved-photo-places` | place | savedPlace |
| 장소 삭제 | DELETE | `/saved-photo-places/{savedPlaceId}` | 없음 | success |

요청 데이터:

```json
{
  "placeId": "string",
  "name": "아사쿠사 센소지",
  "address": "도쿄 다이토구 아사쿠사 2-3-1",
  "category": "사찰·관광지",
  "latitude": 35.7148,
  "longitude": 139.7967,
  "sourcePhotoId": "string"
}
```

응답 데이터:

```json
{
  "savedPlaceId": "string",
  "placeId": "string",
  "name": "아사쿠사 센소지",
  "address": "도쿄 다이토구 아사쿠사 2-3-1",
  "category": "사찰·관광지",
  "latitude": 35.7148,
  "longitude": 139.7967
}
```

연결 화면:

- `/explore`: 장소 저장
- `/plan`: 저장 장소 목록 표시

MVP 대체 지점:

- `savedPhotoPlacesProvider`의 in-memory list를 서버 동기화 provider로 교체한다.
- 중복 기준은 장소명에서 `savedPlaceId` 또는 `placeId`로 변경한다.

### AI 일정 설계 API

필요 API:

| 기능 | Method | Endpoint 초안 | 요청 | 응답 |
| --- | --- | --- | --- | --- |
| 경로 최적화 | POST | `/plans/optimize-route` | tripId, candidates | optimizedRoute |
| 최적화 결과 확정 | POST | `/trips/{tripId}/plans` | optimizedRouteId | plan |

요청 데이터:

```json
{
  "tripId": "string",
  "date": "2025-04-03",
  "startTime": "09:00",
  "endTime": "20:00",
  "transportMode": "transit",
  "candidates": [
    {
      "placeId": "string",
      "name": "아사쿠사 센소지",
      "latitude": 35.7148,
      "longitude": 139.7967,
      "expectedStayMinutes": 90
    }
  ]
}
```

응답 데이터:

```json
{
  "optimizedRouteId": "string",
  "totalTravelMinutes": 74,
  "places": [
    {
      "order": 1,
      "placeId": "string",
      "name": "아사쿠사 센소지",
      "category": "사찰·관광지",
      "arrivalTime": "09:00",
      "departureTime": "10:30",
      "stayMinutes": 90,
      "transportFromPrevious": "도보 8분"
    }
  ]
}
```

연결 화면:

- `/plan`

MVP 대체 지점:

- `routePlaces` mock 결과를 API 응답의 `places`로 교체한다.
- `routeOptimizationProvider`를 `AsyncValue<RouteOptimizationResult>` 기반으로 확장한다.
- `confirmedRouteProvider`는 일정 확정 저장 API 응답과 동기화한다.

### 여행 기록 API

필요 API:

| 기능 | Method | Endpoint 초안 | 요청 | 응답 |
| --- | --- | --- | --- | --- |
| 기록 요약 조회 | GET | `/trips/{tripId}/memorial/summary` | 없음 | summary |
| 날짜별 기록 조회 | GET | `/trips/{tripId}/memorial/days` | 없음 | days |

응답 데이터:

```json
{
  "summary": {
    "days": 4,
    "places": 12,
    "distanceKm": 38.4
  },
  "days": [
    {
      "date": "2025-04-01",
      "places": ["나리타 공항", "아사쿠사", "신주쿠"],
      "photos": [
        {
          "photoId": "string",
          "url": "https://example.com/photo.jpg",
          "takenAt": "2025-04-01T10:20:00+09:00",
          "latitude": 35.7148,
          "longitude": 139.7967
        }
      ]
    }
  ]
}
```

연결 화면:

- `/memorial`

MVP 대체 지점:

- `memorialSummary`, `memorialDays` mock 데이터를 API 응답으로 교체한다.
- 사진 URL 로딩 실패 시 placeholder를 보여준다.

## 7. 화면별 빈 상태, 에러, 피드백

### 공통 피드백 규칙

- 저장 성공, 중복 저장, 준비 중 기능은 스낵바로 안내한다.
- API 연결 후 네트워크 실패는 화면 상단 또는 버튼 근처 inline error로 표시한다.
- 로딩 중 버튼은 비활성화하거나 로딩 indicator를 표시한다.
- 사용자가 취소할 수 있는 흐름은 선택 취소 시 기존 화면을 유지한다.

### 주요 상태별 UI

| 화면 | 상태 | 표시 방식 |
| --- | --- | --- |
| `/explore` | 이미지 선택 전 | 사진 업로드 영역과 최근 탐색 표시 |
| `/explore` | 분석 중 | LinearProgressIndicator |
| `/explore` | 분석 성공 | 장소 결과 카드 |
| `/explore` | 분석 실패 | 실패 안내와 다시 시도 버튼 |
| `/plan` | 저장 장소 없음 | 저장 장소 섹션 숨김 |
| `/plan` | 후보 2개 미만 | 최적화 버튼 비활성화 |
| `/plan` | 최적화 중 | 버튼 내부 loading indicator |
| `/plan` | 최적화 성공 | 최적 경로 결과 카드 |
| `/auth` | validation 실패 | 스낵바 |
| `/mypage` | 기능 미구현 | 준비 중 스낵바 |

## 8. 2주 작업 단위

### 1단계: 명세와 범위 고정

- 프론트엔드 명세서 작성
- MVP 포함/제외 범위 확정
- 보류 항목 문구가 화면과 README에 남아 있는지 점검
- 현재 구현과 명세 차이 목록 작성

### 2단계: 핵심 3축 완성

- 사진 탐색 결과 저장 흐름 안정화
- 저장 장소가 일정 설계에 반영되는 흐름 검증
- AI 경로 최적화 mock 결과 표시 polish
- 여행 기록 화면 이미지 placeholder와 요약 카드 정리

### 3단계: 공통 UX 정리

- 스낵바 문구 통일
- 준비 중 액션 처리
- 버튼 로딩/비활성 상태 점검
- 모바일 폭 카드/텍스트 오버플로우 점검
- 마스코트 사용 위치와 브랜드명 표기 통일

### 4단계: 백엔드 연결 준비

- Repository/DTO 구조 초안 문서화
- mock 데이터와 API 응답 필드 매핑
- 이미지 업로드, 장소 저장, 경로 최적화 API 연결 지점 정리
- 실제 API 연결 전 필요한 백엔드 요청사항 정리

### 5단계: 테스트와 시연 QA

- 위젯 테스트 보강
- 라우팅 직접 진입 확인
- 모바일/데스크톱 브라우저 QA
- 발표 시연 순서 고정
- README 실행/검증 명령 정리

## 9. 테스트 및 QA 명세

### 정적 검사

```bash
flutter analyze
flutter test
flutter build web
```

### 위젯 테스트

- 홈 진입 시 `치와와`, 오늘 일정, 하단 탭이 표시된다.
- `/auth`에서는 하단 탭이 표시되지 않는다.
- 마이페이지 `계정 연결`을 누르면 `/auth`로 이동한다.
- 첫 진입 시 Google 로그인 화면이 표시된다.
- 로그인 없이 둘러보기를 누르면 홈으로 이동한다.
- Mock Google 로그인 후 마이페이지에 이메일 연결 상태가 반영된다.
- OAuth code 딥링크를 처리하면 callback API 결과의 `access_token`이 저장된다.
- 탐색 결과에서 `일정에 추가`를 누르면 저장 스낵바가 표시된다.
- 동일 장소를 다시 저장하면 중복 안내가 표시된다.
- 일정 화면에서 `사진으로 저장한 장소` 섹션이 표시된다.
- 저장 장소 chip을 누르면 일정 후보 chip에 반영된다.
- AI 경로 최적화 실행 후 결과 카드가 표시된다.
- 보류 항목 문구가 신규 노출되지 않는다.

### 브라우저 QA

- `/home`, `/plan`, `/explore`, `/memorial`, `/mypage`, `/auth` 직접 진입이 가능하다.
- 모바일 폭에서 텍스트와 카드가 겹치지 않는다.
- 데스크톱 폭에서 모바일 콘텐츠가 중앙 정렬된다.
- 사진 탐색에서 장소 저장 후 일정 설계 화면에 반영된다.
- 일정 설계에서 확정한 경로가 Memorial 확정 일정 preview에 반영된다.
- mock 설정 row 클릭 시 스낵바가 표시된다.
- 콘솔에 렌더링 에러가 없어야 한다.

### 발표 시연 추천 흐름

1. `/home`에서 현재 여행과 오늘 일정을 보여준다.
2. 하단 탭에서 `/explore`로 이동한다.
3. 최근 탐색 또는 사진 업로드 mock으로 장소 결과를 보여준다.
4. `일정에 추가`로 장소를 저장한다.
5. `/plan`으로 이동해 `사진으로 저장한 장소`를 일정 후보에 추가한다.
6. `AI 경로 최적화`를 실행해 결과를 보여준다.
7. `이 일정으로 확정하기`를 눌러 기록 화면 preview로 넘긴다.
8. `/memorial`에서 확정 일정 preview와 여행 기록 요약을 보여준다.
9. `/mypage`에서 계정/설정과 여행 관리 진입점을 보여준다.

## 10. 구현 시 주의사항

- 보류 항목은 새 UI, 테스트명, mock 데이터, 문서 본문 기능 설명에 추가하지 않는다.
- 실제 기능이 없는 버튼은 빈 콜백으로 두지 않고 스낵바를 연결한다.
- 네트워크 이미지 사용 시 실패 placeholder를 고려한다.
- 사진 탐색과 일정 설계 사이 데이터 흐름은 MVP의 핵심이므로 회귀 테스트를 유지한다.
- 다크 모드는 현재 구현이 없으므로 명세와 UI에서 제외한다.
- React/Vite prototype은 참고용이며 최종 구현 기준은 Flutter 앱이다.
