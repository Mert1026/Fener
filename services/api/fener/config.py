from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql+psycopg://fener@localhost:5432/fener"
    fener_admin_key: SecretStr = SecretStr("")
    fener_app_mode: str = "private"
    fener_snapshot_dir: Path = Path(".data/snapshots")
    openrouter_api_key: SecretStr = SecretStr("")
    llm_stats_api_key: SecretStr = SecretStr("")
    fener_sync_interval_seconds: int = Field(default=21600, ge=3600)
    fener_openrouter_endpoint_limit: int = Field(default=20, ge=0, le=1000)
    auto_apply_recommendations: bool = False
    fener_personal_features_enabled: bool = False
    openai_api_key: SecretStr = SecretStr("")
    zai_api_key: SecretStr = SecretStr("")
    fener_research_provider: Literal["openai", "zai"] = "openai"
    fener_zai_research_model: str = "glm-4.7-flash"
    fener_research_model: str = "gpt-5.4-mini"
    fener_research_daily_limit: int = Field(default=5, ge=1, le=100)


@lru_cache
def settings() -> Settings:
    return Settings()
