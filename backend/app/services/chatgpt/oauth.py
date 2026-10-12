"""OAuth « Sign in with ChatGPT », d'après le SDK officiel (openai/sign-in-with-chatgpt-devkit).

Connexion par le navigateur avec PKCE et nonce ; l'application est enregistrée
dynamiquement au premier passage (client_id=dynamic_agent_client), puis on réutilise
l'identifiant client attribué. Le jeton d'identité est vérifié (signature RS256, émetteur,
audience, nonce) avant toute utilisation des jetons d'accès.
"""

import base64
import hashlib
import hmac
import re
import secrets
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt

from app.services.chatgpt.store import Connection, Credentials, PendingRefresh

ISSUER = "https://auth.openai.com"
RESOURCE = "https://api.openai.com/v1"
SCOPES = "openid profile email offline_access resource.invoke chatgpt.tokens.use.direct"
CALLBACK_PATH = "/auth/callback"
DYNAMIC_CLIENT = "dynamic_agent_client"
LOGIN_TTL_SECONDS = 600
REFRESH_MARGIN_SECONDS = 60
CLIENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,200}$")


class ChatGPTAuthError(Exception):
    """Erreur de connexion, avec un code stable et un message pour l'utilisateur."""

    def __init__(self, code: str, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


def _random() -> str:
    return secrets.token_urlsafe(32)


def _challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


@dataclass
class PendingLogin:
    state: str
    nonce: str
    verifier: str
    redirect_uri: str
    created_at: float = field(default_factory=time.time)

    def expired(self) -> bool:
        return time.time() - self.created_at > LOGIN_TTL_SECONDS


@dataclass(frozen=True)
class Identity:
    subject: str
    email: str
    name: str


class ChatGPTAuth:
    def __init__(self, http: httpx.AsyncClient | None = None) -> None:
        self.http = http or httpx.AsyncClient(timeout=30)
        self._discovery: dict[str, str] | None = None
        self._jwks: dict[str, Any] | None = None

    async def discovery(self) -> dict[str, str]:
        if self._discovery is None:
            try:
                response = await self.http.get(f"{ISSUER}/.well-known/openid-configuration")
                data = response.json()
            except (httpx.HTTPError, ValueError) as exc:
                raise _unavailable() from exc
            keys = ("authorization_endpoint", "token_endpoint", "jwks_uri")
            if (
                response.status_code != 200
                or data.get("issuer") != ISSUER
                or any(not str(data.get(k, "")).startswith(ISSUER + "/") for k in keys)
            ):
                raise ChatGPTAuthError(
                    "discovery_failed", "La configuration de connexion ChatGPT est invalide.", True
                )
            self._discovery = {k: str(v) for k, v in data.items() if isinstance(v, str)}
        return self._discovery

    async def start_login(
        self,
        redirect_uri: str,
        app_name: str,
        host_id: str,
        previous: Connection | None,
    ) -> tuple[str, PendingLogin]:
        config = await self.discovery()
        pending = PendingLogin(_random(), _random(), _random(), redirect_uri)
        params = {
            "client_id": previous.client_id if previous else DYNAMIC_CLIENT,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": SCOPES,
            "resource": RESOURCE,
            "state": pending.state,
            "nonce": pending.nonce,
            "code_challenge_method": "S256",
            "code_challenge": _challenge(pending.verifier),
            "ext_agent_host_id": host_id,
        }
        if previous is None:
            params["agent_name_hint"] = app_name
        elif previous.email:
            params["login_hint"] = previous.email
        return f"{config['authorization_endpoint']}?{urlencode(params)}", pending

    async def finish_login(
        self, params: dict[str, str], pending: PendingLogin, previous: Connection | None
    ) -> Connection:
        if "error" in params:
            raise ChatGPTAuthError(
                "access_denied", "La connexion n'a pas été terminée. Tu peux réessayer."
            )
        code = params.get("code", "")
        client_id = params.get("client_id") or (previous.client_id if previous else "")
        if (
            not code
            or not CLIENT_ID_PATTERN.match(client_id)
            or client_id == DYNAMIC_CLIENT
            or (previous is not None and client_id != previous.client_id)
        ):
            raise ChatGPTAuthError(
                "registration_incomplete", "ChatGPT n'a pas terminé l'enregistrement. Réessaie."
            )
        data = await self._token_request(
            {
                "grant_type": "authorization_code",
                "client_id": client_id,
                "code": code,
                "code_verifier": pending.verifier,
                "redirect_uri": pending.redirect_uri,
                "resource": RESOURCE,
            }
        )
        id_token = data.get("id_token")
        if not isinstance(id_token, str) or not id_token:
            raise ChatGPTAuthError("invalid_id_token", "ChatGPT n'a pas renvoyé d'identité.")
        identity = await self.verify_identity(id_token, client_id, pending.nonce)
        if previous is not None and previous.subject and identity.subject != previous.subject:
            raise ChatGPTAuthError(
                "account_mismatch",
                "Ce n'est pas le même compte ChatGPT que la connexion d'origine.",
            )
        scopes, credentials = _token_fields(data)
        return Connection(
            client_id=client_id,
            subject=identity.subject,
            email=identity.email,
            name=identity.name,
            scopes=scopes,
            credentials=credentials,
            model=previous.model if previous else "",
        )

    async def refresh(self, connection: Connection) -> tuple[Connection, bool]:
        """Renvoie (connexion, à_vérifier).

        Les nouveaux jetons sont mis de côté tant que l'identité renvoyée n'est pas
        vérifiée : un jeton de rafraîchissement ne sert qu'une fois.
        """
        if connection.credentials is None or not connection.credentials.refresh_token:
            raise _reauth()
        data = await self._token_request(
            {
                "grant_type": "refresh_token",
                "client_id": connection.client_id,
                "refresh_token": connection.credentials.refresh_token,
                "resource": RESOURCE,
            }
        )
        data.setdefault("scope", " ".join(connection.scopes))
        scopes, credentials = _token_fields(data, require_refresh=True)
        id_token = data.get("id_token")
        if isinstance(id_token, str) and id_token:
            pending = PendingRefresh(credentials=credentials, scopes=scopes, id_token=id_token)
            return connection.model_copy(update={"pending_refresh": pending}), True
        return connection.model_copy(update={"credentials": credentials, "scopes": scopes}), False

    async def complete_refresh(self, connection: Connection) -> Connection:
        pending = connection.pending_refresh
        if pending is None:
            return connection
        identity = await self.verify_identity(pending.id_token, connection.client_id, None)
        if identity.subject != connection.subject:
            raise ChatGPTAuthError(
                "account_mismatch", "L'identité ChatGPT a changé. Reconnecte-toi."
            )
        return connection.model_copy(
            update={
                "credentials": pending.credentials,
                "scopes": pending.scopes,
                "email": identity.email or connection.email,
                "name": identity.name or connection.name,
                "pending_refresh": None,
            }
        )

    async def revoke(self, connection: Connection) -> bool:
        """Révoque la session distante. Renvoie False si ce n'a pas pu être confirmé."""
        token = (
            connection.pending_refresh.credentials.refresh_token
            if connection.pending_refresh
            else connection.credentials.refresh_token
            if connection.credentials
            else None
        )
        if not token:
            return True
        try:
            endpoint = (await self.discovery()).get("revocation_endpoint")
            if not endpoint:
                return False
            response = await self.http.post(
                endpoint,
                data={
                    "token": token,
                    "token_type_hint": "refresh_token",
                    "client_id": connection.client_id,
                },
            )
        except (httpx.HTTPError, ChatGPTAuthError):
            return False
        return response.status_code == 200

    async def verify_identity(self, id_token: str, client_id: str, nonce: str | None) -> Identity:
        config = await self.discovery()
        try:
            header = jwt.get_unverified_header(id_token)
            key = await self._signing_key(config["jwks_uri"], str(header.get("kid", "")))
        except (jwt.PyJWTError, KeyError) as exc:
            raise _invalid_identity() from exc
        try:
            claims = jwt.decode(
                id_token,
                key,
                algorithms=["RS256"],
                audience=client_id,
                issuer=ISSUER,
                leeway=5,
                options={"require": ["iss", "aud", "exp", "iat", "sub"]},
            )
        except jwt.PyJWTError as exc:
            raise _invalid_identity() from exc
        subject = claims.get("sub")
        azp = claims.get("azp")
        audience = claims.get("aud")
        if (
            not isinstance(subject, str)
            or not subject
            or (nonce is not None and not hmac.compare_digest(str(claims.get("nonce", "")), nonce))
            or (azp is not None and azp != client_id)
            or (isinstance(audience, list) and len(audience) > 1 and azp != client_id)
        ):
            raise _invalid_identity()
        return Identity(
            subject=subject,
            email=str(claims.get("email", "")),
            name=str(claims.get("name", "")),
        )

    async def _signing_key(self, jwks_uri: str, kid: str) -> Any:
        for attempt in (1, 2):
            if self._jwks is None or attempt == 2:
                try:
                    response = await self.http.get(jwks_uri)
                    body = response.json()
                except (httpx.HTTPError, ValueError) as exc:
                    raise _unavailable() from exc
                if response.status_code != 200 or not isinstance(body.get("keys"), list):
                    raise _unavailable()
                self._jwks = body
            for key in jwt.PyJWKSet.from_dict(self._jwks).keys:
                if key.key_id == kid:
                    return key.key
        raise _invalid_identity()

    async def _token_request(self, form: dict[str, str]) -> dict[str, Any]:
        config = await self.discovery()
        try:
            response = await self.http.post(
                config["token_endpoint"], data=form, headers={"Accept": "application/json"}
            )
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise _unavailable() from exc
        if response.status_code != 200 or not isinstance(data, dict):
            code = str(data.get("error", "")) if isinstance(data, dict) else ""
            if code in {
                "invalid_grant",
                "invalid_refresh_token",
                "refresh_token_expired",
                "refresh_token_reused",
                "refresh_token_invalidated",
                "token_expired",
            }:
                raise _reauth()
            if response.status_code >= 500:
                raise _unavailable()
            raise ChatGPTAuthError(code or "token_error", "ChatGPT a refusé la connexion.")
        return data


def _token_fields(
    data: dict[str, Any], require_refresh: bool = False
) -> tuple[list[str], Credentials]:
    scope = data.get("scope")
    if not isinstance(scope, str):
        raise ChatGPTAuthError(
            "invalid_token_response", "Autorisations non confirmées par ChatGPT."
        )
    scopes = scope.split()
    access_token = data.get("access_token")
    expires_in = data.get("expires_in")
    refresh_token = data.get("refresh_token")
    needs_refresh = require_refresh or "offline_access" in scopes
    if (
        not isinstance(access_token, str)
        or not access_token
        or str(data.get("token_type", "")).lower() != "bearer"
        or not isinstance(expires_in, int | float)
        or expires_in <= 0
        or (needs_refresh and (not isinstance(refresh_token, str) or not refresh_token))
    ):
        raise ChatGPTAuthError("invalid_token_response", "Jetons incomplets renvoyés par ChatGPT.")
    return scopes, Credentials(
        access_token=access_token,
        refresh_token=refresh_token if isinstance(refresh_token, str) else None,
        expires_at=time.time() + float(expires_in),
    )


def _unavailable() -> ChatGPTAuthError:
    return ChatGPTAuthError(
        "chatgpt_auth_unavailable",
        "Le service de connexion ChatGPT ne répond pas. Réessaie dans un instant.",
        True,
    )


def _invalid_identity() -> ChatGPTAuthError:
    return ChatGPTAuthError(
        "invalid_id_token", "L'identité ChatGPT n'a pas pu être vérifiée. Reconnecte-toi."
    )


def _reauth() -> ChatGPTAuthError:
    return ChatGPTAuthError(
        "chatgpt_reauth", "La connexion ChatGPT a expiré : reconnecte-toi dans les Réglages."
    )
