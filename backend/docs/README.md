# Backend Docs

백엔드 문서는 실행 중인 API 표면, 구조 설명, 내부 계약을 분리해서 관리한다.

## 현재 성숙도

- 개발·프론트엔드 연동용 프로토타입이다.
- 여행 도메인 상태는 메모리에만 저장되며 재시작 시 초기화된다.
- Google 사용자와 여행별 Memorial 사진 메타데이터는 Git에서 제외된 로컬
  SQLite 파일에 저장된다.
- 사진 원본은 모바일 앱 로컬 저장소가 소유하며 백엔드는 원본 파일을 저장하지
  않는다.
- `/api/v1/auth/me`, 사진 장소 검색, 회원 단위 Memorial API
  (`/api/v1/memorial/*`)가 JWT 보호 대상이며 나머지 여행 API는 현재 공개다.
- 사진 장소 검색은 `ai/image_search`와 Google Maps·Cloud Vision·Gemini를
  호출하고, AI 일정·동선 최적화·주변 추천·빈 시간 추천은 모의 휴리스틱이다.

## 빠른 링크

| 문서 | 역할 |
| --- | --- |
| [api/reference.md](./api/reference.md) | 전체 HTTP API 목록과 Swagger/OpenAPI 접근 경로 |
| [api/auth.md](./api/auth.md) | Google OAuth와 JWT 인증 흐름 |
| [api/memorial.md](./api/memorial.md) | 휴대폰 로컬 사진 메타데이터와 여행 기록 조회 |
| [architecture/backend.md](./architecture/backend.md) | FastAPI 백엔드 모듈 구조와 요청 처리 흐름 |
| [contracts/ai-planning-dto.md](./contracts/ai-planning-dto.md) | 백엔드와 AI 플래너 사이의 내부 DTO 계약 |

## 정리 원칙

1. Swagger UI와 OpenAPI JSON을 API 스키마의 최종 기준으로 둔다.
2. Markdown API 문서는 사람이 빠르게 훑는 색인과 흐름 설명에 집중한다.
3. 하나의 문서는 하나의 책임만 가진다.
4. 외부 HTTP API 문서는 `api/` 아래에 둔다.
5. 모듈 구조와 요청 처리 방식은 `architecture/` 아래에 둔다.
6. 백엔드와 다른 모듈 사이의 내부 계약은 `contracts/` 아래에 둔다.
7. 파일명은 내용 중심의 kebab-case로 쓴다.
8. 날짜, 작성자, 버전처럼 금방 낡는 메타데이터는 커밋 기록으로 대체한다.
9. 라우트나 DTO가 바뀌면 `api/reference.md`와 관련 상세 문서를 함께 갱신한다.
10. 예시는 핵심 흐름만 남기고, 전체 필드 구조는 Swagger UI로 확인하게 한다.
