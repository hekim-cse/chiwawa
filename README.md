# 🐶 치와와 Chiwawa

<p align="center"><img src="assets/images/project_cover_global.png" width="100%" alt="치와와 글로벌 자유여행 플래너" /></p>

<h3 align="center">사진에서 시작해 실제 이동 가능한 일정까지</h3>

<p align="center">
  사진 속 여행지를 실제 장소로 확정하고,<br>
  실제 이동시간을 기반으로 일정과 빈 시간을 설계하는<br>
  <strong>글로벌 자유여행 플래너</strong>
</p>

<p align="center">
  <a href="https://github.com/hekim-cse/chiwawa/actions/workflows/ai-image-search-ci.yml"><img src="https://github.com/hekim-cse/chiwawa/actions/workflows/ai-image-search-ci.yml/badge.svg" alt="AI Image Search CI" /></a>
  <a href="https://github.com/hekim-cse/chiwawa/actions/workflows/ai-route-planner-ci.yml"><img src="https://github.com/hekim-cse/chiwawa/actions/workflows/ai-route-planner-ci.yml/badge.svg" alt="AI Route Planner CI" /></a>
  <a href="https://github.com/hekim-cse/chiwawa/actions/workflows/modal-image-search-deploy.yml"><img src="https://github.com/hekim-cse/chiwawa/actions/workflows/modal-image-search-deploy.yml/badge.svg" alt="Modal Image Search Deploy" /></a>
  <a href="https://github.com/hekim-cse/chiwawa/actions/workflows/modal-route-planner-deploy.yml"><img src="https://github.com/hekim-cse/chiwawa/actions/workflows/modal-route-planner-deploy.yml/badge.svg" alt="Modal Route Planner Deploy" /></a>
</p>

<p align="center"><strong>Flutter · FastAPI · Modal · Google Cloud Vision · Gemini · Google Places · Google Routes</strong></p>

---

<a id="quick-summary"></a>

## 🔎 30초 프로젝트 요약

치와와는 사진에서 발견한 여행지를 실제 장소로 확정하고, 사용자가 선택한 장소를
실제 이동시간에 따라 날짜별로 배정·최적화하며, 빈 시간과 여행 기록까지 연결하는
5인 팀 프로젝트입니다.

| 구분 | 내용 |
|---|---|
| 핵심 개발 기간 | 2026.07.02 ~ 2026.07.27 |
| 팀 구성 | 5명 · PM·AI 개발 1명 · AI 개발 1명 · Backend 2명 · Frontend 1명 |
| 해결 문제 | 사진 장소 식별 · 이동 순서 설계 · 빈 시간 활용 · 여행 기록 |
| 핵심 기술 | Flutter · FastAPI · Modal · SQLite · Google Cloud/Maps APIs |
| 최적화 범위 | 정적 이동시간 Matrix와 정의한 목적함수, 기본 POI 12개 이하 |
| 자동 배포 범위 | Image Search·Route Planner·Free Time Recommender Modal 서비스 |

> 핵심 기능 개발 이후에는 문서와 통합 품질을 지속적으로 보완했습니다.

## 📑 목차

1. [Demo와 사용자 흐름](#demo)
2. [문제와 해결](#problem-and-solution)
3. [핵심 기능](#features)
4. [시스템 아키텍처](#system-architecture)
5. [팀원별 역할 및 구현 범위](#team-contributions)
6. [핵심 엔지니어링](#engineering)
7. [팀 전체 구현·검증 범위](#implementation)
8. [현재 한계와 확장 기준](#limitations)
9. [실행 방법](#quick-start)
10. [기술 스택과 상세 문서](#documentation)
11. [협업 방식](#collaboration)

<br>

<a id="demo"></a>

## 🎬 Demo와 사용자 흐름

<p align="center"><img src="assets/images/project_user_flow_global.png" width="100%" alt="치와와 사용자 서비스 흐름" /></p>

```text
사진 업로드
→ 실제 장소 확정
→ 일정 후보 등록
→ 이동수단별 경로 최적화
→ 빈 시간 추천
→ 일정 확정
→ Memorial 기록
```

<br>

<a id="problem-and-solution"></a>

## 💡 문제와 해결

| 여행자가 겪는 문제 | 치와와의 해결 |
|---|---|
| 사진 속 장소의 이름과 위치를 모름 | Vision·Gemini로 후보를 추론하고 Places로 실제 장소를 확정 |
| 여러 장소의 방문 날짜와 순서를 직접 계산해야 함 | 실제 이동시간 Matrix와 DP로 날짜·방문 순서를 계산 |
| 일정 종료 전 남는 시간을 활용하기 어려움 | 고정 도착시각 안에 삽입 가능한 장소를 카테고리별로 추천 |
| 여행 사진과 방문 기록 정리가 번거로움 | 사진 촬영시각·위치를 날짜별 Memorial과 Paw Map으로 구성 |

<br>

<a id="features"></a>

## ✨ 핵심 기능

### 1. 사진으로 장소 탐색

- 이미지 형식과 MIME 타입 검증
- Cloud Vision 랜드마크 감지와 Gemini 장소명·카테고리 추론
- Google Places 기반 Place ID·주소·좌표·평점 확정
- 동일 Place ID 중복 제거와 주변 장소 후보 제공
- 분석된 장소를 기존 일정 후보와 같은 계약으로 저장

### 2. 일정·경로 최적화

- 출발지와 도착지의 장소·시각 고정
- 사진·검색·추천으로 추가한 장소 자동 병합
- 날짜별 장소 배정과 방문 순서 계산
- 도보·자동차·대중교통별 이동시간 비교
- Route Option과 도착·출발·체류 Timeline 생성
- 확정 결과를 SQLite에 저장하고 홈 일정과 동기화

### 3. 빈 시간 추천

- 최적화 결과의 마지막 방문지부터 고정 도착지까지 남은 시간 계산
- Route Geometry 주변의 카테고리별 장소 검색
- 후보 방문에 필요한 이동·체류·우회시간 평가
- 사용자가 정한 도착시각을 넘지 않는 후보만 반환
- 추천 장소의 일정 후보 추가·삭제와 재최적화 흐름 연결

### 4. 여행 기록 Memorial

- 회원별 사진 원본 파일과 촬영시각·위치 메타데이터 저장
- 날짜별 사진 그리드와 Timeline 구성
- 위치 보정과 Paw Map 동선 시각화
- 여행 요약과 공유 UI 제공

<br>

<a id="system-architecture"></a>

## 🏗️ 시스템 아키텍처

<p align="center"><img src="assets/images/project_architecture_final.png" width="100%" alt="치와와 전체 시스템 아키텍처" /></p>

```text
Flutter App / Web ↔ FastAPI Backend ↔ SQLite

FastAPI → Modal Image Search
            → Cloud Vision · Gemini · Google Places

FastAPI → Modal Route Planner
            → Places에서 확정된 좌표 입력
            → Google Routes 이동시간 행렬

Route Planner → Free Time Recommender
                  → Google Places 후보 검색
                  → Google Routes 우회 이동 계산

FastAPI Google OAuth + JWT ↔ Google OAuth
```

Frontend는 화면과 사용자 입력을 담당하고, Backend는 인증·서비스 상태·영속화와 AI
호출을 조정합니다. Modal AI 서비스는 사진 장소 분석과 조합최적화를 실행하며,
Google API는 실제 장소·좌표·이동시간 데이터를 제공합니다.

> [!NOTE]
> Route Planner는 배포 구조상 AI Services 영역에 포함되어 있지만, 방문 순서 계산
> 자체는 학습 모델이 아니라 결정론적 조합최적화 알고리즘으로 수행합니다.

<br>

<a id="team-contributions"></a>

## 👥 팀원별 역할 및 구현 범위

치와와는 기능별 담당자가 개발한 모듈을 공통 DTO와 API 계약을 기준으로
Frontend·Backend·AI 서비스로 통합한 5인 팀 프로젝트입니다.

| 팀원 | 역할 | 주요 담당 영역 |
|---|---|---|
| 김&#8288;형&#8288;은 | PM&nbsp;·&nbsp;AI&nbsp;개발 | 날짜별 장소 배정, Held–Karp 방문 순서 최적화, Route Option·Timeline, 빈 시간 추천 연동, Backend–AI DTO, AI 평가·회귀 테스트, GitHub Actions·Modal 배포 |
| 박&#8288;재&#8288;우 | AI&nbsp;개발 | 사진 기반 장소 탐색, Cloud Vision·Gemini 분석, Google Places 장소 확정, Image Search 계약·Modal 서비스 |
| 김&#8288;정&#8288;민 | Backend | FastAPI API 기반 구축, Google OAuth·JWT, Backend–AI 연동, 서비스 상태·영속화, Memorial·사진 API |
| 김&#8288;채&#8288;연 | Backend | Memorial API·사진 저장, EXIF·위치·시간대 처리, 일정 검증, AI 통합 DTO 보완, Backend Docker 구성 |
| 고&#8288;윤&#8288;재 | Frontend | Flutter App·Web, Riverpod 상태 관리, 여행·일정·탐색·Memorial 화면, AI Route Option·Timeline 사용자 흐름 |

### 담당 영역 상세 문서

| 담당 | 상세 문서 |
|---|---|
| Route Planning·Recommendation·AI Delivery | [`ai/route_planner/README.md`](ai/route_planner/README.md) |
| Image Search | [`ai/image_search/README.md`](ai/image_search/README.md) |
| Backend | [`backend/README.md`](backend/README.md) |
| Frontend | [`frontend/README.md`](frontend/README.md) |

<br>

<a id="engineering"></a>

## 🧩 핵심 엔지니어링

### AI 추론과 장소 사실을 분리했습니다

사진 모델이 생성한 장소명과 좌표를 그대로 일정에 사용하면 환각이 실제 동선에
전파될 수 있습니다. AI는 장소 후보와 근거를 추론하고, 일정에 사용하는 Place ID·
좌표·주소·평점은 Google Places 응답으로 다시 확정합니다.

```text
Cloud Vision + Gemini       Google Places
장소 후보·근거 추론    →    실제 장소·좌표 확정
```

Places도 잘못된 동명이 장소를 선택할 수 있으므로, 환각을 완전히 제거했다기보다
생성형 추론과 실제 장소 데이터의 경계를 분리해 위험을 줄인 구조입니다.

### 정의한 목적함수와 입력 범위에서는 정확해를 계산합니다

Route Planner는 Google Routes가 제공한 정적 이동시간 Matrix, 고정 출발지·도착지,
기본 POI 12개 이하와 구현된 사전식 목적함수를 전제로 정확한 날짜 배정과 방문
순서를 계산합니다.

- Held–Karp DP로 날짜 내부 방문 순서 계산
- Partition DP로 전체 장소의 날짜별 배정
- 필수 방문 여부와 미배정 장소 수를 우선하는 사전식 목적함수
- 동일 입력에 동일 결과를 반환하는 결정성
- 지원 범위를 넘으면 임의 근사값 대신 명시적 실패

이는 실시간 교통 변화, 영업시간, 예약 가능성이나 사용자 만족 전체에 대한 절대적인
최적을 의미하지 않습니다. Solver 구조와 평가는
[`ai/route_planner/README.md`](ai/route_planner/README.md)에서 확인할 수 있습니다.

### 빈 시간을 경로 삽입 문제로 정의했습니다

후보가 가깝다는 이유만으로 추천하지 않고, 기존 구간을 후보 방문으로 대체할 때의
추가 이동시간과 체류시간을 계산합니다.

```text
현재 장소
→ 추천 후보까지 이동
→ 후보 체류
→ 다음 장소 또는 고정 도착지까지 이동
→ 사용자 도착시각 안에 들어오는지 검증
```

추천은 원본 일정을 자동 변경하지 않습니다. 사용자가 후보를 일정에 추가하면 전체
Route Planner를 다시 실행해 다른 장소와의 상호작용까지 검증합니다.

### 확정 상태를 서버의 단일 기준으로 유지했습니다

사진이나 빈 시간 추천에서 추가한 장소가 화면에만 존재하면 재최적화·일정 확정·홈
조회 과정에서 사라질 수 있습니다. 모든 장소를 `wanted place` 계약으로 정규화하고,
확정 Route Option과 생성된 일정 항목을 SQLite에 함께 저장합니다.

- 최적화 Preview와 일정 Confirm 분리
- 서버가 마지막으로 발급한 Timeline과 확정 요청 비교
- 여행·등록 장소·확정 경로 영속화
- 같은 결과의 중복 확정을 방지하는 멱등 처리
- 확정 후 Riverpod Provider 갱신으로 홈·일정 화면 동기화

<br>

<a id="implementation"></a>

## 🚀 팀 전체 구현·검증 범위

아래 내용은 특정 개인의 단독 구현이 아니라 팀이 역할을 나누어 완성한 전체 서비스
범위입니다. 개인별 구현 경계는 팀원별 역할 표와 상세 문서에서 구분합니다.

| 영역 | 구현 내용 | 주요 검증 |
|---|---|---|
| Frontend | Flutter App·Web, Riverpod, Dio API Repository | 정적 분석, 단위·Widget 테스트, Web Build |
| Backend | FastAPI, Pydantic, Google OAuth·JWT, SQLite | Format, Lint, Type Check, API·Service 테스트, Wheel Build |
| Image Search | Vision·Gemini 분석, Places 사실 확정 | 입력 검증, Provider 계약, 장소 확정 흐름 |
| Route Planner | 정확 일자 배정, 방문 순서, Route Option·Timeline | 완전성, 결정성, Fixture 평가, E2E Benchmark |
| Free Time Recommender | 경로 주변 검색, 우회 지표, 삽입 검증 | 시간 제약, 후보 삽입, 카테고리별 추천 |
| Memorial | 사진 파일·메타데이터, Paw Map·Timeline | EXIF·시간대·파일 저장과 API 회귀 |
| CI/CD | GitHub Actions와 Modal 자동 배포 | PR 회귀 테스트, `main` 반영 후 AI 배포 |

```text
main 반영
→ GitHub Actions 변경 경로 감지
→ AI 단위·계약·E2E 회귀 테스트
→ Modal Image Search 배포
→ Modal Route Planner·Free Time Recommender 배포
```

현재 저장소에서 자동 배포가 확인되는 범위는 Modal AI 서비스입니다. FastAPI와
Flutter는 Docker·로컬 실행 구성을 제공하며, 운영 호스팅 주소는 저장소에 포함하지
않습니다.

자동 테스트는 코드 정확성·계약·회귀를 검증하며, 실제 사용자 만족도나 Google API의
운영 가용성을 증명하는 지표는 아닙니다. Route Planner의 상세 평가와 Benchmark는
[`ai/route_planner/README.md`](ai/route_planner/README.md)에서 별도로 관리합니다.

<br>

<a id="limitations"></a>

## ⚠️ 현재 한계와 확장 기준

| 현재 구조 | 선택 이유 | 전환이 필요한 조건 |
|---|---|---|
| Exact DP·기본 POI 12개 | 제한된 입력에서 정확성·재현성 우선 | 후보 증가 시 OR-Tools·휴리스틱 Hybrid |
| SQLite·프로세스 내 상태 | 단일 인스턴스 프로젝트의 운영 단순성 | 다중 인스턴스 시 PostgreSQL·Redis |
| 동기 Modal 요청 | 사용자 요청과 결과 흐름 단순화 | 장시간·동시 요청 증가 시 Job Queue·Polling |
| 로컬 Memorial 파일 | 프로젝트 범위에서 구현 단순성 | 다중 인스턴스 시 Object Storage |
| 외부 Google API 의존 | 실제 장소·이동 데이터 사용 | Cache·Rate Limit·Retry·Circuit Breaker |
| 일부 프로토타입 API | 통합 사용자 흐름 우선 검증 | 운영 공개 전 사용자 소유권 검증 확대 |

<br>

<a id="quick-start"></a>

## ▶️ 실행 방법

### Backend

```bash
git clone https://github.com/hekim-cse/chiwawa.git
cd chiwawa/backend

cp .env.example .env
uv sync --frozen

PYTHONPATH=..:src \
uv run uvicorn chiwawa_backend.main:app \
  --reload --host 127.0.0.1 --port 8000
```

### Frontend

```bash
cd frontend
flutter pub get

flutter run -d chrome \
  --dart-define=USE_API=true \
  --dart-define=API_BASE_URL=http://127.0.0.1:8000
```

`USE_API`를 지정하지 않으면 화면 검증용 Mock Repository를 사용할 수 있습니다.
필요한 환경변수와 상세 실행 방법은 [Backend README](backend/README.md)와
[Frontend README](frontend/README.md)를 참고해 주세요.

<br>

<a id="documentation"></a>

## 🛠️ 기술 스택과 상세 문서

| 구분 | 기술 | 사용 목적 |
|---|---|---|
| Frontend | Flutter, Dart, Riverpod, Dio | App·Web UI, 상태와 API 통신 |
| Backend | FastAPI, Pydantic v2 | REST API와 요청·응답 계약 검증 |
| Persistence | SQLite | 여행·등록 장소·확정 일정·경로 저장 |
| Authentication | Google OAuth, JWT | Google 로그인과 API 접근 토큰 |
| Image AI | Cloud Vision, Gemini | 랜드마크 감지와 장소 후보 추론 |
| Place·Route Data | Google Places, Routes | 장소 사실 확정과 이동시간 계산 |
| Optimization | Held–Karp DP, Partition DP | 방문 순서와 날짜 배정의 정확 계산 |
| Runtime·Delivery | Modal, Docker, GitHub Actions | 실행환경 패키징, 테스트와 AI 배포 |

### 문서 Index

| 파트 | 문서 |
|---|---|
| Frontend | [`frontend/README.md`](frontend/README.md) |
| Backend | [`backend/README.md`](backend/README.md) |
| Backend API | [`backend/docs/api/reference.md`](backend/docs/api/reference.md) |
| Image Search | [`ai/image_search/README.md`](ai/image_search/README.md) |
| Route Planner | [`ai/route_planner/README.md`](ai/route_planner/README.md) |
| Free Time Recommender | [`ai/free_time_recommender/README.md`](ai/free_time_recommender/README.md) |
| AI Image Search 계약 | [`contracts/ai_image_search/README.md`](contracts/ai_image_search/README.md) |
| AI Route Planner 계약 | [`contracts/ai_route_planner/README.md`](contracts/ai_route_planner/README.md) |

### 저장소 구조

```text
chiwawa/
├── frontend/                       # Flutter App + Web
├── backend/                        # FastAPI Backend
├── ai/
│   ├── image_search/               # 사진 기반 장소 확정
│   ├── route_planner/              # 정확 일정·경로 최적화
│   └── free_time_recommender/      # 경로 삽입 후보 추천
├── contracts/                      # Backend–AI JSON 계약
├── docs/                            # API와 담당 영역 상세 문서
├── artifacts/                      # 평가·Benchmark 결과
├── assets/images/                  # README 이미지
├── .github/workflows/              # CI와 Modal 배포
├── Dockerfile
└── README.md
```

<br>

<a id="collaboration"></a>

## 🤝 협업 방식

치와와는 기능별 작업 브랜치와 Pull Request 리뷰를 통해 개발했습니다. 개발 완료 후
운영 브랜치는 `main`으로 단일화했습니다.

```text
기능 브랜치 → 로컬 테스트 → Pull Request → Review → main 병합
→ GitHub Actions 검증·Modal 배포
```

커밋은 `feat`, `fix`, `refactor`, `docs`, `test`, `chore` 타입으로 변경 목적을
구분했습니다.

---

<p align="center">
  <strong>🐶 복잡한 건 치와 두고 일단 와</strong><br>
  사진에서 시작해 일정과 이동, 여행 기록까지 이어지는 글로벌 여행 플래너
</p>
