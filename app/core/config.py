from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "tinyops"
    app_version: str = "0.1.0"
    environment: str = "dev"

    database_url: str
    redis_url: str
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    
    # Celery configuration
    celery_broker_url: str | None = None
    celery_result_backend: str | None = None
    
    @property
    def celery_broker(self) -> str:
        """Get Celery broker URL, defaulting to redis_url."""
        return self.celery_broker_url or self.redis_url.replace("/0", "/0")
    
    @property
    def celery_backend(self) -> str:
        """Get Celery result backend URL, defaulting to redis_url with db 1."""
        return self.celery_result_backend or self.redis_url.replace("/0", "/1")

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()