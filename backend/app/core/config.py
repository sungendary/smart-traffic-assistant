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
    kakao_rest_api_key: str = Field(default="")

    # Weather API (OpenWeatherMap)
    openweather_api_key: str = Field(default="")

    cors_origins: str = Field(default="http://localhost:5173,http://localhost:3000,http://localhost")

    llm_base_url: str = Field(default="http://llm:11434")
    llm_model: str = Field(default="qwen2.5:0.5b")
    llm_temperature: float = Field(default=0.2)
    
    # Google Gemini API 설정
    gemini_api_key: str = Field(default="", description="Google Gemini API 키 (환경 변수: GEMINI_API_KEY)")
    gemini_model: str = Field(default="gemini-3-pro-preview")
    
    admin_email: str = Field(default="")  # 관리자 이메일 (관리자 API 접근용)

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
