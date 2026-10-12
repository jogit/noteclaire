import asyncio
import os
import stat
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from urllib.parse import parse_qs, urlparse

import httpx2
import openai
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from openai import AsyncOpenAI

from app.config import Settings
from app.main import create_app
from app.services.ai.base import (
    AIProviderError,
    PhotoRequest,
    StructureRequest,
    StructureResult,
)
from app.services.ai.chatgpt_provider import ChatGPTProvider, parse_json_text
from app.services.chatgpt.oauth import ChatGPTAuth, ChatGPTAuthError
from app.services.chatgpt.session import ChatGPTSession
from app.services.chatgpt.store import CONNECTION_FILE, CredentialStore, StoreError
from tests.chatgpt_fakes import CLIENT_ID, FakeOpenAIAuth


@pytest.fixture
def fake() -> FakeOpenAIAuth:
    return FakeOpenAIAuth()


@pytest.fixture
def session(tmp_path: Path, fake: FakeOpenAIAuth) -> ChatGPTSession:
    return ChatGPTSession(CredentialStore(tmp_path), ChatGPTAuth(fake.client()), 8080, "")


def query(url: str) -> dict[str, str]:
    return {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}


def connect(session: ChatGPTSession, fake: FakeOpenAIAuth) -> dict[str, str]:
    params = query(asyncio.run(session.start_login()))
    fake.nonce = params["nonce"]
    asyncio.run(
        session.finish_login({"code": "code-1", "state": params["state"], "client_id": CLIENT_ID})
    )
    return params


# --- Connexion -------------------------------------------------------------------------


def test_login_url(session: ChatGPTSession) -> None:
    url = asyncio.run(session.start_login())
    assert url.startswith("https://auth.openai.com/oauth/authorize?")
    params = query(url)
    assert params["client_id"] == "dynamic_agent_client"
    assert params["agent_name_hint"] == "NoteClaire"
    assert params["redirect_uri"] == "http://127.0.0.1:8080/auth/callback"
    assert params["resource"] == "https://api.openai.com/v1"
    assert "chatgpt.tokens.use.direct" in params["scope"].split()
    assert params["code_challenge_method"] == "S256"
    assert params["ext_agent_host_id"].startswith("urn:uuid:")
    assert len(params["state"]) > 30 and params["state"] != params["nonce"]


def test_finish_login_stores_encrypted_connection(
    session: ChatGPTSession, fake: FakeOpenAIAuth, tmp_path: Path
) -> None:
    connect(session, fake)

    form = fake.forms[-1]
    assert form["grant_type"] == "authorization_code"
    assert form["client_id"] == CLIENT_ID
    assert form["code_verifier"] and form["redirect_uri"].endswith("/auth/callback")
    status = session.status()
    assert (status.connected, status.email, status.name) == (True, "eleve@example.org", "Élève")
    stored = (tmp_path / "secrets" / CONNECTION_FILE).read_bytes()
    assert b"access-1" not in stored and b"refresh-1" not in stored
    for name in ("credentials.key", CONNECTION_FILE):
        mode = stat.S_IMODE(os.stat(tmp_path / "secrets" / name).st_mode)
        assert mode == 0o600


@pytest.mark.parametrize(
    ("params", "code"),
    [
        ({"code": "c", "state": "inconnu", "client_id": CLIENT_ID}, "invalid_state"),
        ({"code": "c", "client_id": "dynamic_agent_client"}, "registration_incomplete"),
        ({"code": "", "client_id": CLIENT_ID}, "registration_incomplete"),
        ({"error": "access_denied"}, "access_denied"),
    ],
)
def test_finish_login_errors(
    session: ChatGPTSession, fake: FakeOpenAIAuth, params: dict[str, str], code: str
) -> None:
    state = query(asyncio.run(session.start_login()))["state"]
    fake.nonce = "x"
    params = {"state": state} | params
    with pytest.raises(ChatGPTAuthError) as error:
        asyncio.run(session.finish_login(params))
    assert error.value.code == code
    assert session.status().connected is False


def test_wrong_nonce_is_rejected(session: ChatGPTSession, fake: FakeOpenAIAuth) -> None:
    state = query(asyncio.run(session.start_login()))["state"]
    fake.nonce = "un-autre-nonce"
    with pytest.raises(ChatGPTAuthError) as error:
        asyncio.run(session.finish_login({"code": "c", "state": state, "client_id": CLIENT_ID}))
    assert error.value.code == "invalid_id_token"


def test_state_is_single_use(session: ChatGPTSession, fake: FakeOpenAIAuth) -> None:
    params = connect(session, fake)
    with pytest.raises(ChatGPTAuthError) as error:
        asyncio.run(
            session.finish_login({"code": "c", "state": params["state"], "client_id": CLIENT_ID})
        )
    assert error.value.code == "invalid_state"


def test_reconnection_reuses_registration(session: ChatGPTSession, fake: FakeOpenAIAuth) -> None:
    connect(session, fake)
    asyncio.run(session.disconnect())
    params = query(asyncio.run(session.start_login()))
    assert params["client_id"] == CLIENT_ID
    assert params["login_hint"] == "eleve@example.org"
    assert "agent_name_hint" not in params


def test_other_account_is_rejected_on_reconnection(
    session: ChatGPTSession, fake: FakeOpenAIAuth
) -> None:
    connect(session, fake)
    fake.subject = "quelqu-un-d-autre"
    with pytest.raises(ChatGPTAuthError) as error:
        connect(session, fake)
    assert error.value.code == "account_mismatch"


# --- Jetons ----------------------------------------------------------------------------


def expire(session: ChatGPTSession) -> None:
    connection = session.store.load()
    assert connection is not None and connection.credentials is not None
    credentials = connection.credentials.model_copy(update={"expires_at": time.time() - 1})
    session.store.save(connection.model_copy(update={"credentials": credentials}))


def test_valid_token_is_reused(session: ChatGPTSession, fake: FakeOpenAIAuth) -> None:
    connect(session, fake)
    assert asyncio.run(session.access_token()) == "access-1"
    assert len(fake.forms) == 1


def test_expired_token_is_refreshed(session: ChatGPTSession, fake: FakeOpenAIAuth) -> None:
    connect(session, fake)
    expire(session)

    assert asyncio.run(session.access_token()) == "access-2"

    form = fake.forms[-1]
    assert (form["grant_type"], form["refresh_token"]) == ("refresh_token", "refresh-1")
    assert asyncio.run(session.access_token()) == "access-2"  # sauvegardé


def test_refresh_survives_key_service_outage(session: ChatGPTSession, fake: FakeOpenAIAuth) -> None:
    connect(session, fake)
    expire(session)
    fake.jwks_down = True
    session.auth._jwks = None  # oublie les clés en cache

    with pytest.raises(ChatGPTAuthError) as error:
        asyncio.run(session.access_token())
    assert error.value.retryable

    fake.jwks_down = False
    assert asyncio.run(session.access_token()) == "access-2"
    # Le jeton de rafraîchissement déjà consommé n'a pas été réutilisé.
    assert [f["grant_type"] for f in fake.forms] == ["authorization_code", "refresh_token"]


def test_refused_refresh_requires_new_sign_in(
    session: ChatGPTSession, fake: FakeOpenAIAuth
) -> None:
    connect(session, fake)
    expire(session)
    fake.token_error = "invalid_grant"
    with pytest.raises(ChatGPTAuthError) as error:
        asyncio.run(session.access_token())
    assert error.value.code == "chatgpt_reauth"


def test_not_connected(session: ChatGPTSession) -> None:
    with pytest.raises(ChatGPTAuthError) as error:
        asyncio.run(session.access_token())
    assert error.value.code == "chatgpt_not_connected"


def test_disconnect_revokes(session: ChatGPTSession, fake: FakeOpenAIAuth) -> None:
    connect(session, fake)
    assert asyncio.run(session.disconnect()) is True
    revoke = next(r for r in fake.requests if r.url.path == "/oauth/revoke")
    assert b"token=refresh-1" in revoke.content
    status = session.status()
    assert (status.connected, status.needs_reauth) == (False, True)


def test_models_and_choice(session: ChatGPTSession, fake: FakeOpenAIAuth) -> None:
    connect(session, fake)
    models = asyncio.run(session.list_models())
    assert [m.slug for m in models] == ["gpt-6-luna", "gpt-6-sol"]
    models_request = next(r for r in fake.requests if r.url.path == "/v1/models")
    assert models_request.headers["authorization"] == "Bearer access-1"

    assert asyncio.run(session.resolve_model()) == "gpt-6-luna"  # premier proposé
    asyncio.run(session.set_model("gpt-6-sol"))
    assert session.status().model == "gpt-6-sol"


def test_unreadable_store_is_not_overwritten(tmp_path: Path) -> None:
    store = CredentialStore(tmp_path)
    store.host_id()
    (tmp_path / "secrets" / CONNECTION_FILE).write_bytes(b"pas chiffre")
    with pytest.raises(StoreError):
        store.load()
    assert (tmp_path / "secrets" / CONNECTION_FILE).read_bytes() == b"pas chiffre"


# --- Provider --------------------------------------------------------------------------

REQUEST = StructureRequest(subject="Maths", chapter="Vecteurs", raw_notes="vecteur AB")
HTTP_REQUEST = httpx2.Request("POST", "https://api.openai.com/v1/responses")


class FakeStream:
    """Flux d'événements tel que renvoyé par la voie ChatGPT : réponse finale sans contenu."""

    def __init__(self, outcome: Any) -> None:
        self.outcome = outcome

    async def __aenter__(self) -> "FakeStream":
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    def __aiter__(self) -> Any:
        async def events() -> Any:
            for event in self.outcome:
                yield event

        return events()


def events(text: str, *, completed: bool = True, chunk: int = 7) -> list[SimpleNamespace]:
    stream = [SimpleNamespace(type="response.created")]
    stream += [
        SimpleNamespace(type="response.output_text.delta", delta=text[i : i + chunk])
        for i in range(0, len(text), chunk)
    ]
    if completed:
        stream.append(
            SimpleNamespace(
                type="response.completed",
                response=SimpleNamespace(output=[], usage=usage()),
            )
        )
    return stream


class FakeResponses:
    def __init__(self, *outcomes: Any) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[dict[str, Any]] = []

    def stream(self, **kwargs: Any) -> FakeStream:
        self.calls.append(kwargs)
        return FakeStream(self.outcomes.pop(0))


def api_error(status: int, code: str, param: str | None = None) -> openai.APIStatusError:
    response = httpx2.Response(status, request=HTTP_REQUEST)
    body = {"code": code, "param": param}
    cls = openai.BadRequestError if status == 400 else openai.RateLimitError
    return cls("erreur", response=response, body=body)


def provider_with(
    session: ChatGPTSession, responses: FakeResponses
) -> tuple[ChatGPTProvider, list[str]]:
    tokens: list[str] = []

    def factory(token: str) -> AsyncOpenAI:
        tokens.append(token)
        return cast(AsyncOpenAI, SimpleNamespace(responses=responses))

    return ChatGPTProvider(session, factory), tokens


def usage() -> SimpleNamespace:
    return SimpleNamespace(input_tokens=11, output_tokens=7)


def test_provider_structured_request(session: ChatGPTSession, fake: FakeOpenAIAuth) -> None:
    connect(session, fake)
    responses = FakeResponses(events('{"clean_course": "# Vecteurs"}'))
    provider, tokens = provider_with(session, responses)

    result = asyncio.run(provider.structure_course(REQUEST))

    assert result.result.clean_course == "# Vecteurs"
    assert (result.input_tokens, result.output_tokens) == (11, 7)
    assert tokens == ["access-1"]
    [call] = responses.calls
    assert call["input"] == [{"role": "user", "content": call["input"][0]["content"]}]
    assert "vecteur AB" in call["input"][0]["content"]
    assert call["store"] is False
    assert call["text_format"] is StructureResult
    assert call["model"] == "gpt-6-luna"
    assert provider.paid is False


def test_provider_sends_photo_as_image(session: ChatGPTSession, fake: FakeOpenAIAuth) -> None:
    connect(session, fake)
    responses = FakeResponses(events('{"text": "vecteur AB", "uncertain": []}'))
    provider, _ = provider_with(session, responses)

    result = asyncio.run(
        provider.transcribe_photo(
            PhotoRequest(
                subject="Maths", chapter="Vecteurs", image_data_url="data:image/jpeg;base64,AA"
            )
        )
    )

    assert result.result.text == "vecteur AB"
    [message] = responses.calls[0]["input"]
    assert [part["type"] for part in message["content"]] == ["input_text", "input_image"]
    assert message["content"][1]["image_url"] == "data:image/jpeg;base64,AA"


def test_provider_falls_back_to_json_prompt(session: ChatGPTSession, fake: FakeOpenAIAuth) -> None:
    connect(session, fake)
    responses = FakeResponses(
        api_error(400, "subscription_sharing_unsupported_capability"),
        events('```json\n{"clean_course": "# Vecteurs"}\n```'),
        events('{"clean_course": "# Encore"}'),
    )
    provider, _ = provider_with(session, responses)

    assert asyncio.run(provider.structure_course(REQUEST)).result.clean_course == "# Vecteurs"
    assert asyncio.run(provider.structure_course(REQUEST)).result.clean_course == "# Encore"

    first, second, third = responses.calls
    assert "text_format" in first and "text_format" not in second and "text_format" not in third
    assert "objet JSON valide" in second["instructions"]


def test_provider_requires_completed_stream(session: ChatGPTSession, fake: FakeOpenAIAuth) -> None:
    connect(session, fake)
    responses = FakeResponses(
        events('{"clean_course": "# Vec', completed=False),
        [SimpleNamespace(type="response.failed", response=None)],
    )
    provider, _ = provider_with(session, responses)
    with pytest.raises(AIProviderError) as error:
        asyncio.run(provider.structure_course(REQUEST))
    assert error.value.code == "ai_invalid_response"
    with pytest.raises(AIProviderError) as error:
        asyncio.run(provider.structure_course(REQUEST))
    assert error.value.code == "ai_unavailable"


def test_provider_usage_limit(session: ChatGPTSession, fake: FakeOpenAIAuth) -> None:
    connect(session, fake)
    responses = FakeResponses(api_error(429, "subscription_sharing_usage_limit_exceeded"))
    provider, _ = provider_with(session, responses)
    with pytest.raises(AIProviderError) as error:
        asyncio.run(provider.structure_course(REQUEST))
    assert error.value.code == "chatgpt_usage_limit"


def test_provider_requires_connection(session: ChatGPTSession) -> None:
    provider, _ = provider_with(session, FakeResponses())
    with pytest.raises(AIProviderError) as error:
        asyncio.run(provider.structure_course(REQUEST))
    assert error.value.code == "chatgpt_not_connected"


def test_parse_json_text() -> None:
    assert parse_json_text('Voici : {"clean_course": "x"} !', StructureResult).clean_course == "x"
    with pytest.raises(AIProviderError):
        parse_json_text("pas de json", StructureResult)
    with pytest.raises(AIProviderError):
        parse_json_text('{"autre": 1}', StructureResult)


# --- API -------------------------------------------------------------------------------


@pytest.fixture
def chatgpt_app(settings: Settings, fake: FakeOpenAIAuth) -> FastAPI:
    app = create_app(settings.model_copy(update={"ai_provider": "chatgpt"}))
    app.state.chatgpt.auth = ChatGPTAuth(fake.client())
    return app


def test_api_sign_in_flow(chatgpt_app: FastAPI, fake: FakeOpenAIAuth) -> None:
    with TestClient(chatgpt_app, base_url="http://localhost:8080") as client:
        status = client.get("/api/chatgpt/status").json()
        assert (status["ai_provider"], status["connected"]) == ("chatgpt", False)
        assert status["redirect_uri"] == "http://127.0.0.1:8080/auth/callback"

        url = client.post("/api/chatgpt/login").json()["authorization_url"]
        params = query(url)
        fake.nonce = params["nonce"]
        response = client.get(
            "/auth/callback",
            params={"code": "c", "state": params["state"], "client_id": CLIENT_ID},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/reglages?chatgpt=connecte"

        status = client.get("/api/chatgpt/status").json()
        assert (status["connected"], status["email"]) == (True, "eleve@example.org")
        models = client.get("/api/chatgpt/models").json()
        assert [m["slug"] for m in models] == ["gpt-6-luna", "gpt-6-sol"]
        assert client.put("/api/chatgpt/model", json={"model": "gpt-6-sol"}).status_code == 204
        assert client.get("/api/chatgpt/status").json()["model"] == "gpt-6-sol"

        assert client.post("/api/chatgpt/logout").json() == {"revoked": True}
        assert client.get("/api/chatgpt/status").json()["connected"] is False


def test_api_callback_with_bad_state(chatgpt_app: FastAPI) -> None:
    with TestClient(chatgpt_app) as client:
        response = client.get(
            "/auth/callback", params={"code": "c", "state": "faux"}, follow_redirects=False
        )
    assert response.headers["location"] == "/reglages?chatgpt=erreur&code=invalid_state"


def test_api_models_require_connection(chatgpt_app: FastAPI) -> None:
    with TestClient(chatgpt_app) as client:
        response = client.get("/api/chatgpt/models")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "chatgpt_not_connected"


def test_ai_requires_connection(chatgpt_app: FastAPI) -> None:
    with TestClient(chatgpt_app) as client:
        subject_id = client.get("/api/subjects").json()[1]["id"]
        chapter_id = client.post(
            "/api/chapters", json={"subject_id": subject_id, "title": "Vecteurs"}
        ).json()["id"]
        client.put(f"/api/chapters/{chapter_id}/notes", json={"raw_text": "vecteur AB"})
        response = client.post(f"/api/chapters/{chapter_id}/structure")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "chatgpt_not_connected"


def test_callback_is_public_but_api_is_protected(settings: Settings) -> None:
    app = create_app(settings.model_copy(update={"app_password": "secret"}))
    with TestClient(app) as client:
        assert client.get("/api/chatgpt/status").status_code == 401
        response = client.get("/auth/callback", params={"state": "x"}, follow_redirects=False)
        assert response.status_code == 303


def test_callback_secrets_are_masked_in_access_log() -> None:
    import logging

    from app.main import RedactCallbackQuery

    record = logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        "",
        0,
        '%s - "%s %s HTTP/%s" %d',
        ("10.0.0.1:1", "GET", "/auth/callback?code=secret&state=s", "1.0", 303),
        None,
    )
    RedactCallbackQuery().filter(record)
    assert "secret" not in record.getMessage()
    assert "/auth/callback?[masqué]" in record.getMessage()


def test_redirect_uri_is_always_the_loopback_address(chatgpt_app: FastAPI) -> None:
    """OpenAI impose l'adresse de boucle locale, quelle que soit l'adresse du site."""
    with TestClient(chatgpt_app, base_url="https://noteclaire.exemple.fr") as client:
        expected = "http://127.0.0.1:8080/auth/callback"
        assert client.get("/api/chatgpt/status").json()["redirect_uri"] == expected
        url = client.post("/api/chatgpt/login").json()["authorization_url"]
        assert query(url)["redirect_uri"] == expected
