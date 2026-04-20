# Backend

This package contains the FileSh backend API, domain logic, persistence layer, Alembic migrations, and the cleanup worker.

## Responsibilities

- User authentication and session management
- Workspace folder and file operations
- Share creation, update, revocation, and shared-link access
- Object upload/download backed by MinIO
- Search and filtered resource listing
- Metrics, structured logs, tracing, and request IDs
- Cleanup/event publishing and worker-side processing through Kafka

## Stack

- Python 3.13
- FastAPI
- SQLAlchemy 2.x
- Alembic
- PostgreSQL with Psycopg
- MinIO
- Kafka
- OpenTelemetry
- Prometheus client
- `uv` for dependency and command management

## Application Layout

```text
backend/
|-- app/
|   |-- api/                  FastAPI routes and HTTP error mapping
|   |-- application/          Use cases, DTOs, shared presenters
|   |-- core/                 Config, DB, security, storage, tracing, observability
|   |-- dependencies/         FastAPI dependency providers
|   |-- domain/               Enums and domain exceptions
|   |-- persistence/models/   SQLAlchemy ORM models
|   |-- repositories/         Data access layer
|   |-- schemas/              Request and response models
|   `-- workers/              Background cleanup worker
|-- alembic/
|-- tests/
|-- pyproject.toml
`-- Dockerfile
```

## API Reference

For the complete and up-to-date API surface, open the Swagger docs after starting the backend:

- `http://localhost:8000/docs`

You can explore request and response schemas there, try endpoints directly, and verify the latest routes without relying on this README.

## Environment Variables

Copy the root `.env.example` file to `.env`, then update the values for your local environment:

```bash
cp .env.example .env
```

Common values in `.env.example`:

```env
DATABASE_URL=postgresql+psycopg://filesh:filesh@postgres:5432/filesh
MINIO_ENDPOINT=minio:9000
MINIO_BUCKET=files
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
MINIO_SECURE=false
KAFKA_BROKER=kafka:9092
JWT_SECRET=change-me-to-a-32-byte-minimum-secret
SHARE_TOKEN_SECRET=change-me-to-a-32-byte-minimum-secret
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
BACKEND_CORS_ORIGINS=http://localhost:5173
BACKEND_CORS_ORIGIN_REGEX=^https?://(localhost|127\.0\.0\.1)(:\d+)?$
```

Additional backend settings are defined in `app/core/config.py`, including logging, metrics, tracing, and Kafka topic controls.

## Run Locally

### With Docker Compose

From the repository root:

```bash
make backend
```

Or start the whole stack:

```bash
make up
```

### Without Docker

You will need PostgreSQL, MinIO, and optionally Kafka running separately.

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Worker

The cleanup worker runs as a separate process and consumes Kafka messages for cleanup-related tasks.

```bash
cd backend
uv sync
uv run python -m app.workers.cleanup
```

When using Compose, the worker is started by the `cleanup-worker` service.

## Development Commands

```bash
cd backend
uv sync
uv run pytest
uv run pytest -n 4 tests
uv run ruff check .
uv run ruff format .
uv run alembic upgrade head
```

## Testing

- Tests live under `backend/tests`
- Coverage is enabled by default
- The configured minimum coverage threshold is `80%`
