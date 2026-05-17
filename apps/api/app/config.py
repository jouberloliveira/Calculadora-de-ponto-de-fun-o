from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ollama_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="llama3")
    max_upload_bytes: int = Field(default=52_428_800)
    job_ttl_seconds: int = Field(default=3600)
    cors_origins: str = Field(default="http://localhost:3000")

    # Ingest safety caps.
    max_decompressed_bytes: int = Field(default=100 * 1024 * 1024)
    max_archive_files: int = Field(default=1000)
    max_text_chars_per_file: int = Field(default=200_000)

    # Ollama client.
    ollama_timeout_seconds: float = Field(default=300.0)
    ollama_max_retries: int = Field(default=3)

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
