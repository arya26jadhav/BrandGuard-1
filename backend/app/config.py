from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    database_url: str = Field(alias="DATABASE_URL")

    @field_validator("database_url", mode="before")
    @classmethod
    def resolve_docker_db_url(cls, v: str) -> str:
        if isinstance(v, str) and Path("/.dockerenv").exists():
            return (
                v.replace("@localhost:5433/", "@db:5432/")
                .replace("@127.0.0.1:5433/", "@db:5432/")
                .replace("@localhost:5432/", "@db:5432/")
                .replace("@127.0.0.1:5432/", "@db:5432/")
            )
        return v
    jwt_secret: str = Field(alias="JWT_SECRET")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    brandguard_model: str = Field(default="gemini-flash-lite-latest", alias="BRANDGUARD_MODEL")
    frontend_origins: str = Field(
        default="http://localhost:5173",
        alias="FRONTEND_ORIGINS",
    )
    env: str = Field(default="development", alias="ENV")
    slack_bot_token: str = Field(default="", alias="SLACK_BOT_TOKEN")
    slack_channel_id: str = Field(default="", alias="SLACK_CHANNEL_ID")

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.frontend_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()