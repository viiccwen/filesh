from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="development", alias="APP_ENV")
    database_url: str = Field(
        default="postgresql+psycopg://filesh:filesh@postgres:5432/filesh",
        alias="DATABASE_URL",
    )
    minio_endpoint: str = Field(default="minio:9000", alias="MINIO_ENDPOINT")
    minio_bucket: str = Field(default="files", alias="MINIO_BUCKET")
    kafka_broker: str = Field(default="kafka:9092", alias="KAFKA_BROKER")
    jwt_secret: str = Field(default="change-me", alias="JWT_SECRET")
    backend_cors_origins: str = Field(
        default="http://localhost:5173",
        alias="BACKEND_CORS_ORIGINS",
    )


settings = Settings()
