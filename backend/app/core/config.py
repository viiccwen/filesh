from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_JWT_SECRET = "change-me-to-a-32-byte-minimum-secret"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="development", alias="APP_ENV")
    database_url: str = Field(
        default="postgresql+psycopg://filesh:filesh@postgres:5432/filesh",
        alias="DATABASE_URL",
    )
    minio_endpoint: str = Field(default="minio:9000", alias="MINIO_ENDPOINT")
    minio_bucket: str = Field(default="files", alias="MINIO_BUCKET")
    minio_root_user: str = Field(default="minioadmin", alias="MINIO_ROOT_USER")
    minio_root_password: str = Field(default="minioadmin", alias="MINIO_ROOT_PASSWORD")
    minio_secure: bool = Field(default=False, alias="MINIO_SECURE")
    kafka_broker: str = Field(default="kafka:9092", alias="KAFKA_BROKER")
    kafka_cleanup_topic: str = Field(default="filesh.cleanup", alias="KAFKA_CLEANUP_TOPIC")
    kafka_cleanup_retry_topic: str = Field(
        default="filesh.cleanup.retry",
        alias="KAFKA_CLEANUP_RETRY_TOPIC",
    )
    kafka_cleanup_dlq_topic: str = Field(
        default="filesh.cleanup.dlq",
        alias="KAFKA_CLEANUP_DLQ_TOPIC",
    )
    kafka_client_id: str = Field(default="filesh-backend", alias="KAFKA_CLIENT_ID")
    kafka_cleanup_group_id: str = Field(
        default="filesh-cleanup-worker",
        alias="KAFKA_CLEANUP_GROUP_ID",
    )
    kafka_cleanup_replay_group_id: str = Field(
        default="filesh-cleanup-dlq-replay",
        alias="KAFKA_CLEANUP_REPLAY_GROUP_ID",
    )
    kafka_cleanup_topic_partitions: int = Field(
        default=3,
        alias="KAFKA_CLEANUP_TOPIC_PARTITIONS",
    )
    kafka_cleanup_retry_topic_partitions: int = Field(
        default=3,
        alias="KAFKA_CLEANUP_RETRY_TOPIC_PARTITIONS",
    )
    kafka_cleanup_dlq_topic_partitions: int = Field(
        default=1,
        alias="KAFKA_CLEANUP_DLQ_TOPIC_PARTITIONS",
    )
    kafka_cleanup_replication_factor: int = Field(
        default=1,
        alias="KAFKA_CLEANUP_REPLICATION_FACTOR",
    )
    kafka_cleanup_max_retries: int = Field(
        default=5,
        alias="KAFKA_CLEANUP_MAX_RETRIES",
    )
    kafka_cleanup_retry_base_seconds: int = Field(
        default=5,
        alias="KAFKA_CLEANUP_RETRY_BASE_SECONDS",
    )
    kafka_cleanup_retry_max_seconds: int = Field(
        default=300,
        alias="KAFKA_CLEANUP_RETRY_MAX_SECONDS",
    )
    kafka_cleanup_dlq_replay_limit: int = Field(
        default=100,
        alias="KAFKA_CLEANUP_DLQ_REPLAY_LIMIT",
    )
    kafka_publisher_enabled: bool = Field(default=False, alias="KAFKA_PUBLISHER_ENABLED")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_json: bool = Field(default=True, alias="LOG_JSON")
    metrics_enabled: bool = Field(default=True, alias="METRICS_ENABLED")
    worker_metrics_port: int = Field(default=9101, alias="WORKER_METRICS_PORT")
    tracing_enabled: bool = Field(default=False, alias="TRACING_ENABLED")
    otel_exporter_otlp_endpoint: str = Field(
        default="http://alloy:4317",
        alias="OTEL_EXPORTER_OTLP_ENDPOINT",
    )
    otel_exporter_otlp_insecure: bool = Field(
        default=True,
        alias="OTEL_EXPORTER_OTLP_INSECURE",
    )
    otel_service_namespace: str = Field(
        default="filesh",
        alias="OTEL_SERVICE_NAMESPACE",
    )
    otel_service_name: str = Field(default="filesh-backend", alias="OTEL_SERVICE_NAME")
    jwt_secret: str = Field(default=DEFAULT_JWT_SECRET, alias="JWT_SECRET")
    share_token_secret: str = Field(default=DEFAULT_JWT_SECRET, alias="SHARE_TOKEN_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=15, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")
    refresh_token_cookie_name: str = Field(
        default="refresh_token",
        alias="REFRESH_TOKEN_COOKIE_NAME",
    )
    refresh_token_cookie_secure: bool = Field(default=False, alias="REFRESH_TOKEN_COOKIE_SECURE")
    backend_cors_origins: str = Field(
        default="http://localhost:5173",
        alias="BACKEND_CORS_ORIGINS",
    )
    backend_cors_origin_regex: str = Field(
        default=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        alias="BACKEND_CORS_ORIGIN_REGEX",
    )

    @field_validator("backend_cors_origin_regex", mode="before")
    @classmethod
    def normalize_cors_origin_regex(cls, value: str) -> str:
        # `.env` files sometimes over-escape regex backslashes. Normalize them
        # so localhost/loopback patterns still work when loaded from env vars.
        if isinstance(value, str):
            return value.replace("\\\\", "\\")
        return value

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]


settings = Settings()
