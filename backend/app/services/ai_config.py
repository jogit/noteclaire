"""Choix de l'IA fait dans l'assistant de premier lancement.

Les valeurs saisies dans l'interface sont rangées, chiffrées comme la connexion ChatGPT, dans
DATA_DIR/secrets/ai.enc et l'emportent sur le fichier .env. La clé n'est jamais renvoyée au
navigateur.
"""

import logging
from typing import Literal

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from app.config import Settings
from app.services.chatgpt.session import ChatGPTSession
from app.services.chatgpt.store import CredentialStore, StoreError

logger = logging.getLogger(__name__)

CONFIG_FILE = "ai.enc"
Provider = Literal["openai", "chatgpt", "local", "fake"]


class AIConfig(BaseModel):
    ai_provider: Provider
    openai_api_key: str = Field(default="", max_length=300)
    local_ai_base_url: str = Field(default="", max_length=300)
    local_ai_model: str = Field(default="", max_length=100)


def normalize_base_url(url: str) -> str:
    """Ajoute `/v1` si l'adresse du serveur local l'omet (LM Studio, Ollama l'exigent)."""
    url = url.strip().rstrip("/")
    return url if not url or url.endswith("/v1") else f"{url}/v1"


def _apply(settings: Settings, config: AIConfig) -> None:
    settings.ai_provider = config.ai_provider
    if config.openai_api_key:
        settings.openai_api_key = config.openai_api_key
    if config.local_ai_base_url:
        settings.local_ai_base_url = normalize_base_url(config.local_ai_base_url)
    if config.local_ai_model:
        settings.local_ai_model = config.local_ai_model


def load_saved_config(settings: Settings) -> None:
    """Applique au démarrage le choix enregistré dans l'interface, s'il existe."""
    try:
        data = CredentialStore(settings.data_dir).read_secret(CONFIG_FILE)
        config = None if data is None else AIConfig.model_validate_json(data)
    except (OSError, ValueError, StoreError):  # fichier abîmé : on repart du .env
        logger.warning("%s illisible : ignoré", CONFIG_FILE)
        return
    if config is not None:
        _apply(settings, config)


def save_config(settings: Settings, config: AIConfig) -> None:
    """Enregistre le choix. Une clé laissée vide garde la clé déjà connue."""
    if not config.openai_api_key:
        config = config.model_copy(update={"openai_api_key": settings.openai_api_key})
    CredentialStore(settings.data_dir).write_secret(CONFIG_FILE, config.model_dump_json().encode())
    _apply(settings, config)


def is_ready(settings: Settings, chatgpt: ChatGPTSession) -> bool:
    """L'IA choisie peut-elle répondre ? (« fake » = essai sans IA, toujours prêt)."""
    match settings.ai_provider:
        case "openai":
            return bool(settings.openai_api_key)
        case "chatgpt":
            return chatgpt.status().connected
        case _:
            return True


async def check_connection(settings: Settings) -> tuple[bool, str]:
    """Teste l'IA choisie sans rien consommer (liste des modèles). Message sans secret."""
    if settings.ai_provider == "fake":
        return True, "Mode essai : les notes sont renvoyées sans modification."
    if settings.ai_provider == "chatgpt":
        return True, "La connexion ChatGPT se fait dans les Réglages."
    if settings.ai_provider == "openai":
        if not settings.openai_api_key:
            return False, "Aucune clé n'est enregistrée."
        client = AsyncOpenAI(api_key=settings.openai_api_key, timeout=15, max_retries=0)
    else:
        client = AsyncOpenAI(
            api_key=settings.local_ai_api_key or "local",
            base_url=settings.local_ai_base_url,
            timeout=15,
            max_retries=0,
        )
    try:
        await client.models.list()
    except Exception:  # message volontairement générique : l'erreur peut contenir la clé
        return False, "Connexion impossible : vérifiez la clé ou l'adresse."
    return True, "Connexion réussie."
