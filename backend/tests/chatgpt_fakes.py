"""Faux serveur d'authentification OpenAI (OIDC) pour les tests : aucun appel réseau."""

import json
import time
from typing import Any
from urllib.parse import parse_qs

import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from app.services.chatgpt.oauth import ISSUER

CLIENT_ID = "client_noteclaire_123"
SUBJECT = "user-42"


class FakeOpenAIAuth:
    def __init__(self) -> None:
        self.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.kid = "key-1"
        self.requests: list[httpx.Request] = []
        self.forms: list[dict[str, str]] = []
        self.nonce = ""
        self.token_count = 0
        self.token_error: str | None = None
        self.jwks_down = False
        self.refresh_id_token = True
        self.subject = SUBJECT

    def id_token(self, nonce: str | None = None, **claims: Any) -> str:
        now = int(time.time())
        payload = {
            "iss": ISSUER,
            "aud": CLIENT_ID,
            "sub": self.subject,
            "iat": now,
            "exp": now + 3600,
            "email": "eleve@example.org",
            "name": "Élève",
        } | claims
        if nonce is not None:
            payload["nonce"] = nonce
        return jwt.encode(payload, self.key, algorithm="RS256", headers={"kid": self.kid})

    def _jwks(self) -> dict[str, Any]:
        jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(self.key.public_key()))
        return {"keys": [jwk | {"kid": self.kid, "alg": "RS256", "use": "sig"}]}

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if path == "/.well-known/openid-configuration":
            return httpx.Response(
                200,
                json={
                    "issuer": ISSUER,
                    "authorization_endpoint": f"{ISSUER}/oauth/authorize",
                    "token_endpoint": f"{ISSUER}/oauth/token",
                    "jwks_uri": f"{ISSUER}/.well-known/jwks.json",
                    "revocation_endpoint": f"{ISSUER}/oauth/revoke",
                },
            )
        if path == "/.well-known/jwks.json":
            return httpx.Response(503) if self.jwks_down else httpx.Response(200, json=self._jwks())
        if path == "/oauth/token":
            form = {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
            self.forms.append(form)
            if self.token_error:
                return httpx.Response(400, json={"error": self.token_error})
            self.token_count += 1
            body: dict[str, Any] = {
                "access_token": f"access-{self.token_count}",
                "refresh_token": f"refresh-{self.token_count}",
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": "openid profile email offline_access resource.invoke "
                "chatgpt.tokens.use.direct",
            }
            if form["grant_type"] == "authorization_code":
                body["id_token"] = self.id_token(self.nonce)
            elif self.refresh_id_token:
                body["id_token"] = self.id_token()
            return httpx.Response(200, json=body)
        if path == "/oauth/revoke":
            return httpx.Response(200)
        if path == "/v1/models":
            return httpx.Response(
                200,
                json={
                    "models": [
                        {"slug": "gpt-6-luna", "display_name": "GPT-6 Luna", "visibility": "list"},
                        {"slug": "interne", "display_name": "Caché", "visibility": "hide"},
                        {"slug": "gpt-6-sol", "display_name": "GPT-6 Sol", "visibility": "list"},
                    ]
                },
            )
        return httpx.Response(404)

    def client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(self.handler))
