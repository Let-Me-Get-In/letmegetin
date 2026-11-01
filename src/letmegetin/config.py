"""Configuration de l'application (variables d'environnement LETMEGETIN_*)."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Paramètres chargés depuis l'environnement ou un fichier .env."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="LETMEGETIN_", extra="ignore")

    environment: str = "development"
    database_url: str = "postgresql+asyncpg://letmegetin:letmegetin@localhost:55433/letmegetin"
    api_title: str = "LetMeGetIn API"
    api_version: str = "0.1.0"
    data_dir: Path = Path("data/referential")
    jwt_secret: str = "dev-insecure-secret-change-me"
    access_token_ttl: int = 900
    refresh_token_ttl: int = 2_592_000
    verification_token_ttl: int = 86_400
    public_base_url: str = "http://localhost:8000"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str = "no-reply@letmegetin.org"
    redis_url: str | None = None
    rate_limit_default_rpm: int = 60
    rate_limit_auth_rpm: int = 10
    rate_limit_window: int = 60
    worker_count: int = 1
    cache_ttl: int = 3600
    sentry_dsn: str | None = None
    git_sha: str = "dev"
    retention_idempotency_hours: int = 24
    retention_refresh_days: int = 30


settings = Settings()
