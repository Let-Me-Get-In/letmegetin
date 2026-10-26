"""Configuration de l'application (variables d'environnement LETMEGETIN_*)."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Paramètres chargés depuis l'environnement ou un fichier .env."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="LETMEGETIN_", extra="ignore")

    database_url: str = "postgresql+asyncpg://letmegetin:letmegetin@localhost:55433/letmegetin"
    api_title: str = "Jaccede API"
    api_version: str = "0.1.0"
    data_dir: Path = Path("data/referential")


settings = Settings()
