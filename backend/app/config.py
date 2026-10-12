from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration lue uniquement depuis les variables d'environnement (ou un fichier .env)."""

    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    app_env: Literal["development", "production", "test"] = "development"
    log_level: str = "INFO"
    app_password: str = ""
    # Numéro de version, fixé au build de l'image (ARG APP_VERSION) ; « dev » depuis les sources.
    app_version: str = "dev"

    database_url: str = "sqlite:////data/app.db"
    data_dir: Path = Path("/data")

    ai_provider: Literal["openai", "local", "chatgpt", "fake"] = "openai"
    openai_api_key: str = ""
    openai_model: str = "gpt-6-luna"
    ai_timeout_seconds: float = 120

    # AI_PROVIDER=local : serveur compatible OpenAI (Ollama, LM Studio, llama.cpp…).
    local_ai_base_url: str = "http://host.docker.internal:11434/v1"
    local_ai_model: str = "qwen3:8b"
    local_ai_api_key: str = ""
    local_ai_timeout_seconds: float = 300

    # AI_PROVIDER=chatgpt : abonnement ChatGPT Plus/Pro (« Sign in with ChatGPT »).
    # Port de l'application sur la machine : OpenAI impose l'adresse de retour
    # http://127.0.0.1:<port>/auth/callback (boucle locale), donc connexion depuis cette machine.
    chatgpt_redirect_port: int = 8080
    chatgpt_model: str = ""

    # Sauvegardes quotidiennes (base + images) ; les plus anciennes sont effacées.
    backup_dir: Path = Path("/backups")
    backup_keep: int = 7
    backups_enabled: bool = True

    # Budget mensuel ; 0 = pas de limite. Les prix servent à estimer le coût de chaque appel.
    ai_monthly_budget_eur: float = 5
    ai_input_price_eur_per_mtok: float | None = None
    ai_output_price_eur_per_mtok: float | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
