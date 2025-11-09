from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # use UPPERCASE env names to match .env
    APP_ENV: str = "local"  # local | dev | prod
    NOTION_TOKEN: str | None = None
    GITHUB_TOKEN: str | None = None
    CALENDAR_ICS_URL: str | None = None
    OPENAI_API_KEY: str | None = None

    # pydantic-settings v2 style
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # ignore stray vars rather than erroring
    )


settings = Settings()
