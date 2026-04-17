.PHONY: up down logs ps backend frontend test lint format compose-config migrate pre-commit-install pre-commit-run

up:
	docker compose --env-file .env up --build -d

down:
	docker compose --env-file .env down

logs:
	docker compose --env-file .env logs -f

ps:
	docker compose --env-file .env ps

backend:
	docker compose --env-file .env up --build backend postgres minio kafka

frontend:
	docker compose --env-file .env up --build frontend backend

test:
	docker compose --env-file .env run --rm backend uv run pytest

lint:
	docker compose --env-file .env run --rm backend uv run ruff check .
	docker compose --env-file .env run --rm frontend pnpm lint

format:
	docker compose --env-file .env run --rm backend uv run ruff format .
	docker compose --env-file .env run --rm frontend pnpm format

compose-config:
	docker compose --env-file .env config

migrate:
	docker compose --env-file .env run --rm backend uv run alembic upgrade head

pre-commit-install:
	cd backend && uv run pre-commit install --config ../.pre-commit-config.yaml

pre-commit-run:
	cd backend && uv run pre-commit run --config ../.pre-commit-config.yaml --all-files
