# Backend Docs

백엔드 문서는 실행 중인 API 표면, 구조 설명, 내부 계약을 분리해서 관리한다.

## 빠른 링크

| 문서 | 역할 |
| --- | --- |
| [api/reference.md](./api/reference.md) | 전체 HTTP API 목록과 Swagger/OpenAPI 접근 경로 |
| [api/auth.md](./api/auth.md) | Google OAuth와 JWT 인증 흐름 |
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
