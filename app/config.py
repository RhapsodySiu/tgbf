from typing import Optional, Literal

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    telegram_bot_token: str = Field(..., description="Telegram Bot Token")
    app_mode: Literal["polling", "webhook"] = Field(..., description="Whether the bot uses polling or webhook mode to handle message")
    webhook_host: Optional[str] = Field(None, description="Webhook Host")
    webhook_path: Optional[str] = Field(None, description="Webhook Path")
    llm_provider: str = Field(..., description="LLM Provider")
    llm_base_url: str = Field(..., description="LLM Base URL")
    data_dir: str = Field(..., description="Database data path")
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()