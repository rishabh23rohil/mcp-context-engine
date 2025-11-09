from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # use UPPERCASE env names to match .env
    APP_ENV: str = "local"  # local | dev | prod
    NOTION_TOKEN: str | None = None
    GITHUB_TOKEN: str | None = None
    CALENDAR_ICS_URL: str | None = None
    OPENAI_API_KEY: str | None = None

    # ⬇️ NEW: non-breaking M3 defaults (overridable via .env)
    DEFAULT_TZ: str = "America/Chicago"
    WORK_HOURS_START: str = "09:00"
    WORK_HOURS_END: str = "18:00"
    AVAILABILITY_EDGE_POLICY: str = "exclusive_end"  # or "inclusive"

    # pydantic-settings v2 style
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # ignore stray vars rather than erroring
    )

settings = Settings()

class Settings(BaseSettings):
    APP_ENV: str = "local"
    NOTION_TOKEN: str | None = None
    GITHUB_TOKEN: str | None = None
    CALENDAR_ICS_URL: str | None = None
    OPENAI_API_KEY: str | None = None

    # NEW: availability defaults (override in .env as needed)
    DEFAULT_TZ: str = "America/Chicago"         # e.g., "America/Chicago"
    WORK_HOURS_START: str = "09:00"
    WORK_HOURS_END: str = "18:00"
    AVAILABILITY_EDGE_POLICY: str = "exclusive_end"  # or "inclusive"
