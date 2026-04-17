.PHONY: up down logs ps backend frontend test lint lint-local format format-local compose-config migrate pre-commit pre-commit-install pre-commit-run

cmd := docker compose --env-file .env

up:
	$(cmd) up --build -d

down:
	$(cmd) down

logs:
	$(cmd) logs -f

ps:
	$(cmd) ps

backend:
	$(cmd) up --build backend postgres minio kafka

frontend:
	$(cmd) up --build frontend backend

test:
	$(cmd) run --rm backend uv run pytest -n 4 tests

lint:
	$(cmd) run --rm backend uv run ruff check .
	$(cmd) run --rm frontend pnpm lint

lint-local:
	cd backend && uv run ruff check .

format:
	$(cmd) run --rm backend uv run ruff format .
	$(cmd) run --rm frontend pnpm format

format-local:
	cd backend && uv run ruff format .

compose-config:
	$(cmd) config

migrate:
	$(cmd) run --rm backend uv run alembic upgrade head

pre-commit: pre-commit-run

pre-commit-install:
	cd backend && uv run pre-commit install --config ../.pre-commit-config.yaml

pre-commit-run:
	cd backend && uv run pre-commit run --config ../.pre-commit-config.yaml --all-files
