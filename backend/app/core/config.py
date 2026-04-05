from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Legal AI Platform"
    app_version: str = "1.0.0"
    environment: str = "development"

    model_config = SettingsConfigDict(
        env_prefix="LEGAL_AI_",
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
