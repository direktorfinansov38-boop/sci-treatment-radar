from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    digest_timezone: str = "Asia/Ulaanbaatar"
    digest_hour: int = 10
    digest_minute: int = 0
    digest_lookback_days: int = 3
    digest_max_items: int = 25

    anthropic_api_key: str | None = None
    claude_model: str = "claude-sonnet-4-6"

    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    email_from: str | None = None
    email_to: str | None = None

    webhook_url: str | None = None
    output_dir: Path = Field(default=Path("digests"))
    queries_path: Path = Field(default=Path("config/queries.json"))
    state_path: Path = Field(default=Path("state/sent_history.json"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
