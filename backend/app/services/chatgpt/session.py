"""Connexion ChatGPT de l'application : connexion, jetons à jour, modèle choisi."""

import asyncio
import logging
import time
from dataclasses import dataclass

import httpx

from app.services.chatgpt.oauth import (
    CALLBACK_PATH,
    REFRESH_MARGIN_SECONDS,
    RESOURCE,
    ChatGPTAuth,
    ChatGPTAuthError,
    PendingLogin,
)
from app.services.chatgpt.store import Connection, CredentialStore, StoreError

logger = logging.getLogger(__name__)

APP_NAME = "NoteClaire"


@dataclass(frozen=True)
class ChatGPTModel:
    slug: str
    display_name: str


@dataclass(frozen=True)
class ChatGPTStatus:
    connected: bool
    email: str
    name: str
    model: str
    needs_reauth: bool


class ChatGPTSession:
    def __init__(
        self, store: CredentialStore, auth: ChatGPTAuth, redirect_port: int, default_model: str
    ) -> None:
        self.store = store
        self.auth = auth
        self.redirect_port = redirect_port
        self.default_model = default_model
        self._pending: dict[str, PendingLogin] = {}
        self._lock = asyncio.Lock()

    @property
    def redirect_uri(self) -> str:
        # Adresse de retour en boucle locale imposée par OpenAI pour les applications locales.
        return f"http://127.0.0.1:{self.redirect_port}{CALLBACK_PATH}"

    def _load(self) -> Connection | None:
        try:
            return self.store.load()
        except StoreError as exc:
            raise ChatGPTAuthError("chatgpt_storage", str(exc)) from exc

    # --- Connexion -----------------------------------------------------------------------

    async def start_login(self, redirect_uri: str | None = None) -> str:
        self._pending = {s: p for s, p in self._pending.items() if not p.expired()}
        previous = self._load()
        if previous is not None and not previous.client_id:
            previous = None
        url, pending = await self.auth.start_login(
            redirect_uri or self.redirect_uri, APP_NAME, self.store.host_id(), previous
        )
        self._pending[pending.state] = pending
        return url

    async def finish_login(self, params: dict[str, str]) -> Connection:
        pending = self._pending.pop(params.get("state", ""), None)
        if pending is None or pending.expired():
            raise ChatGPTAuthError(
                "invalid_state",
                "Cette connexion a expiré ou ne vient pas de NoteClaire. Relance-la depuis "
                "les Réglages.",
            )
        async with self._lock:
            connection = await self.auth.finish_login(params, pending, self._load())
            self.store.save(connection)
        logger.info("chatgpt connected")
        return connection

    async def disconnect(self) -> bool:
        async with self._lock:  # pas pendant un rafraîchissement : il rétablirait la connexion
            connection = self._load()
            if connection is None:
                return True
            revoked = await self.auth.revoke(connection)
            # On garde l'identifiant client et l'e-mail pour une reconnexion plus simple.
            self.store.save(
                connection.model_copy(update={"credentials": None, "pending_refresh": None})
            )
        logger.info("chatgpt disconnected revoked=%s", revoked)
        return revoked

    def status(self) -> ChatGPTStatus:
        try:
            connection = self._load()
        except ChatGPTAuthError:
            return ChatGPTStatus(False, "", "", "", True)
        if connection is None:
            return ChatGPTStatus(False, "", "", "", False)
        connected = connection.credentials is not None or connection.pending_refresh is not None
        return ChatGPTStatus(
            connected=connected,
            email=connection.email,
            name=connection.name,
            model=connection.model or self.default_model,
            needs_reauth=not connected and bool(connection.subject),
        )

    # --- Utilisation ---------------------------------------------------------------------

    async def access_token(self) -> str:
        """Jeton d'accès valide, rafraîchi si nécessaire (un seul rafraîchissement à la fois)."""
        async with self._lock:
            connection = self._load()
            if connection is None or (
                connection.credentials is None and connection.pending_refresh is None
            ):
                raise ChatGPTAuthError(
                    "chatgpt_not_connected",
                    "Connecte ton compte ChatGPT dans les Réglages pour utiliser l'IA.",
                )
            if connection.pending_refresh is None:
                assert connection.credentials is not None
                if connection.credentials.expires_at > time.time() + REFRESH_MARGIN_SECONDS:
                    return connection.credentials.access_token
                connection, to_verify = await self.auth.refresh(connection)
                # Sauvegarde avant vérification : le jeton de rafraîchissement est consommé.
                self.store.save(connection)
                if not to_verify:
                    assert connection.credentials is not None
                    return connection.credentials.access_token
            connection = await self.auth.complete_refresh(connection)
            self.store.save(connection)
            assert connection.credentials is not None
            return connection.credentials.access_token

    async def list_models(self) -> list[ChatGPTModel]:
        token = await self.access_token()
        try:
            response = await self.auth.http.get(
                f"{RESOURCE}/models",
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            )
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ChatGPTAuthError(
                "chatgpt_unavailable", "ChatGPT ne répond pas. Réessaie.", True
            ) from exc
        if response.status_code == 401:
            raise ChatGPTAuthError(
                "chatgpt_reauth", "La connexion ChatGPT a expiré : reconnecte-toi."
            )
        if response.status_code != 200 or not isinstance(body.get("models"), list):
            raise ChatGPTAuthError(
                "chatgpt_unavailable", "La liste des modèles ChatGPT est indisponible.", True
            )
        return [
            ChatGPTModel(str(m["slug"]), str(m.get("display_name") or m["slug"]))
            for m in body["models"]
            if isinstance(m, dict) and m.get("visibility") == "list" and m.get("slug")
        ]

    def current_model(self) -> str:
        connection = self._load()
        return (connection.model if connection else "") or self.default_model

    async def resolve_model(self) -> str:
        """Modèle choisi, sinon celui par défaut, sinon le premier proposé par l'abonnement."""
        model = self.current_model()
        if model:
            return model
        models = await self.list_models()
        if not models:
            raise ChatGPTAuthError(
                "chatgpt_model_unavailable", "Aucun modèle n'est disponible pour ce compte."
            )
        await self.set_model(models[0].slug)
        return models[0].slug

    async def set_model(self, model: str) -> None:
        async with self._lock:  # un rafraîchissement en cours réécrirait l'ancien choix
            connection = self._load()
            if connection is None:
                raise ChatGPTAuthError(
                    "chatgpt_not_connected", "Connecte d'abord ton compte ChatGPT."
                )
            self.store.save(connection.model_copy(update={"model": model}))
