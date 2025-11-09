from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Read APP_ENV from .env, default "local"
    app_env: str = Field(default="local", alias="APP_ENV")

    NOTION_TOKEN: str | None = None
    GITHUB_TOKEN: str | None = None
    CALENDAR_ICS_URL: str | None = None
    OPENAI_API_KEY: str | None = None

    # IMPORTANT: allow extras so unknown env keys don't explode; be case-insensitive
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow",
        case_sensitive=False,
        populate_by_name=True,
    )

settings = Settings()
