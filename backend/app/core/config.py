from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./demo.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "deckgen-uploads"
    UPLOADS_DIR: str = "uploads"
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    @property
    def sync_database_url(self) -> str:
        url = self.DATABASE_URL
        url = url.replace("+aiosqlite", "")
        url = url.replace("+asyncpg", "")
        return url

    model_config = {"env_file": [".env.local", ".env"], "extra": "ignore"}


settings = Settings()
