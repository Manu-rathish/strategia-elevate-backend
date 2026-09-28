from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )
    default_dev_user: str = "jenny.marsh"
    seed_dir: Path = Path("seed")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    def resolved_seed_dir(self) -> Path:
        if self.seed_dir.is_absolute():
            return self.seed_dir
        return Path(__file__).resolve().parents[1] / self.seed_dir


@lru_cache
def get_settings() -> Settings:
    return Settings()
