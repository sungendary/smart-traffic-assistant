from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    project_name: str = "Smart Relationship Navigator"
    api_prefix: str = "/api"

    mongodb_uri: str = Field(default="mongodb://mongo:27017")
    mongodb_db: str = Field(default="datingapp")

    redis_url: str = Field(default="redis://redis:6379/0")

    jwt_secret_key: str = Field(default="change-me")
    jwt_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=15)
    refresh_token_expire_minutes: int = Field(default=60 * 24 * 7)

    password_hash_scheme: str = Field(default="argon2")

    kakao_map_app_key: str = Field(default="")

    cors_origins: str = Field(default="http://localhost:5173,http://localhost:3000,http://localhost")

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def frontend_static_dir(self) -> Path:
        return Path(__file__).resolve().parents[3] / "frontend"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[arg-type]


settings = get_settings()
