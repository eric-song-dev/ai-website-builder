from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "postgresql+psycopg://builder:builder@localhost:5432/builder"
    model_provider: str = "fake"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4.1-mini"
    pexels_api_key: str = ""
    artifact_root: Path = Path("artifacts")
    deployment_root: Path = Path("deployments")
    public_base_url: str = "http://localhost:8000"
    max_files: int = 48
    max_file_bytes: int = 400_000
    max_bundle_bytes: int = 4_000_000


@lru_cache
def get_settings() -> Settings:
    return Settings()
