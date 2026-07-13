.PHONY: sync format format-check lint type test check run

sync:
	uv sync

format:
	uv run ruff format .

format-check:
	uv run ruff format --check .

lint:
	uv run ruff check .

type:
	uv run basedpyright

test:
	uv run pytest

check: format-check lint type test

run:
	uv run uvicorn chiwawa_backend.main:app --reload --no-access-log --host 127.0.0.1 --port 8000
