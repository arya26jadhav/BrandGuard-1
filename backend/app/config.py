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
    smtp_host: str = Field(default="", alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_user: str = Field(default="", alias="SMTP_USER")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    smtp_from: str = Field(default="", alias="SMTP_FROM")
    smtp_starttls: bool = Field(default=True, alias="SMTP_STARTTLS")
    app_base_url: str = Field(default="", alias="APP_BASE_URL")
    embedding_model: str = Field(default="gemini-embedding-001", alias="EMBEDDING_MODEL")
    evidence_top_k: int = Field(default=25, alias="EVIDENCE_TOP_K", ge=1)
    approved_logo_path: str = Field(
        default=str(BACKEND_DIR.parent / "test_data" / "images" / "approved_logo_v3.2.png"),
        alias="APPROVED_LOGO_PATH",
    )
    image_storage_dir: str = Field(
        default=str(BACKEND_DIR / "uploads" / "content_images"),
        alias="IMAGE_STORAGE_DIR",
    )

    # Phase 2 (plan section 7). The vision model must accept images; check it with
    # scripts/check_vision_model.py before changing it. gemini-flash-latest was tested on the key.
    vision_model: str = Field(default="gemini-flash-latest", alias="BRANDGUARD_VISION_MODEL")
    vision_max_calls_per_submission: int = Field(default=10, alias="VISION_MAX_CALLS", ge=1)
    vision_timeout_seconds: int = Field(default=60, alias="VISION_TIMEOUT_SECONDS", ge=1)
    submission_max_mb: int = Field(default=10, alias="SUBMISSION_MAX_MB", ge=1)
    submission_max_files: int = Field(default=10, alias="SUBMISSION_MAX_FILES", ge=1)
    submission_max_pdf_pages: int = Field(default=20, alias="SUBMISSION_MAX_PDF_PAGES", ge=1)

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def cors_origins(self) -> list[str]:
        """Origins exactly as browsers send them: no spaces, no trailing slash."""
        origins = []
        for raw in self.frontend_origins.split(","):
            origin = raw.strip().rstrip("/")
            if origin:
                origins.append(origin)
        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()

def find_origin_problems(origins: list[str]) -> list[str]:
    """Problems with FRONTEND_ORIGINS that would make browser requests fail. Empty when all is well."""
    problems = []
    for origin in origins:
        if origin == "*":
            problems.append("FRONTEND_ORIGINS must list origins, not '*', because credentials are allowed")
        elif not origin.startswith(("https://", "http://")):
            problems.append(f"Origin '{origin}' needs a scheme, for example https://{origin}")
        elif origin.count("/") > 2:
            problems.append(f"Origin '{origin}' should not include a path")
    return problems
