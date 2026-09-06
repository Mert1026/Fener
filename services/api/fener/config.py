from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql+psycopg://fener@localhost:5432/fener"
    fener_admin_key: SecretStr = SecretStr("")
    fener_app_mode: str = "private"
    fener_snapshot_dir: Path = Path(".data/snapshots")
    fener_sync_interval_seconds: int = Field(default=21600, ge=3600)
    auto_apply_recommendations: bool = False
    fener_personal_features_enabled: bool = False
    zai_api_key: SecretStr = SecretStr("")
    fener_zai_research_model: str = "glm-4.7-flash"
    fener_research_daily_limit: int = Field(default=5, ge=1, le=100)


@lru_cache
def settings() -> Settings:
    return Settings()
