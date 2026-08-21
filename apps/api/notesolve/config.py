from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="NOTESOLVE_", extra="ignore")

    env: str = "development"
    data_dir: Path = Path(".notesolve-data")
    max_upload_mb: int = 25
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]
    ai_provider: str = "fake"
    openai_api_key: str | None = None
    openai_model: str = "gpt-5.4"
    openai_base_url: str = "https://api.openai.com/v1"
    verification_enabled: bool = True
    verification_threshold: float = Field(default=0.9, ge=0, le=1)
    openai_verification_model: str | None = None

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def database_url(self) -> str:
        return f"sqlite:///{(self.data_dir / 'notesolve.db').as_posix()}"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
