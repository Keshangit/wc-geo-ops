from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ops_api_key: str = ""
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    log_level: str = "INFO"
    quick_audit_timeout: int = 60

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"
    anthropic_max_tokens: int = 8192

    redis_url: str = "redis://127.0.0.1:6379/0"
    job_ttl_seconds: int = 604800
    rq_queue_name: str = "geo_full_audits"

    wc_geo_webhook_url: str = ""

    full_sitemap_max_pages: int = 20
    full_sample_pages: int = 5

    @property
    def api_key_configured(self) -> bool:
        return bool(self.ops_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
