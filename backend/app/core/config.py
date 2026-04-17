from pydantic import Field
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
    kafka_client_id: str = Field(default="filesh-backend", alias="KAFKA_CLIENT_ID")
    kafka_cleanup_group_id: str = Field(
        default="filesh-cleanup-worker",
        alias="KAFKA_CLEANUP_GROUP_ID",
    )
    kafka_publisher_enabled: bool = Field(default=False, alias="KAFKA_PUBLISHER_ENABLED")
    jwt_secret: str = Field(default=DEFAULT_JWT_SECRET, alias="JWT_SECRET")
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

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]


settings = Settings()
