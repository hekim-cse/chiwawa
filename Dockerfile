# Chiwawa 백엔드 컨테이너 이미지
#   빌드 컨텍스트는 반드시 레포 루트여야 합니다 (백엔드가 루트의 ai/ 모듈에 의존).
#   빌드:  docker build -t chiwawa-backend .
#   실행:  docker run -p 8000:8000 --env-file .env.prod -v /data:/data chiwawa-backend

FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# uv 설치 (astral 공식 이미지에서 바이너리만 복사)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 1) 의존성만 먼저 설치 — 소스가 바뀌어도 이 레이어는 캐시 재사용
COPY backend/pyproject.toml backend/uv.lock /app/backend/
WORKDIR /app/backend
RUN uv sync --frozen --no-install-project --no-dev

# 2) 애플리케이션 소스 복사
COPY backend/src /app/backend/src
COPY ai /app/ai

# hatchling 빌드(force-include)를 피하고 소스 그대로 실행한다.
# ai/ 는 네임스페이스 패키지이므로 레포 루트를 PYTHONPATH에 둔다.
ENV PATH="/app/backend/.venv/bin:$PATH" \
    PYTHONPATH="/app/backend/src:/app"

EXPOSE 8000

# 헬스체크는 /health 사용
CMD ["uvicorn", "chiwawa_backend.main:create_app", "--factory", \
     "--host", "0.0.0.0", "--port", "8000"]
