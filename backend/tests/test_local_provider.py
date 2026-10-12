"""Provider local (Ollama, LM Studio) avec un client simulé : aucun appel réseau."""

import asyncio
from types import SimpleNamespace
from typing import Any, cast

import httpx2 as httpx
import openai
import pytest
from fastapi.testclient import TestClient
from openai import AsyncOpenAI

from app.config import Settings
from app.main import create_app
from app.models import AIRun
from app.services.ai.base import (
    AIProviderError,
    PhotoRequest,
    PhotoResult,
    StructureRequest,
    StructureResult,
)
from app.services.ai.factory import build_ai_provider
from app.services.ai.local_provider import LocalProvider
from tests.conftest import structured

REQUEST = StructureRequest(subject="SVT", chapter="La cellule", raw_notes="la cellule")
HTTP_REQUEST = httpx.Request("POST", "http://ollama:11434/v1/chat/completions")


class FakeCompletions:
    def __init__(self, outcome: Any) -> None:
        self.outcome = outcome
        self.calls: list[dict[str, Any]] = []

    async def parse(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


def make_provider(outcome: Any) -> tuple[LocalProvider, FakeCompletions]:
    completions = FakeCompletions(outcome)
    client = cast(AsyncOpenAI, SimpleNamespace(chat=SimpleNamespace(completions=completions)))
    return LocalProvider(client, "qwen3:8b"), completions


def completion(parsed: Any) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(parsed=parsed))],
        usage=SimpleNamespace(prompt_tokens=30, completion_tokens=12),
    )


def test_structure_with_chat_completions() -> None:
    provider, completions = make_provider(completion(StructureResult(clean_course="# La cellule")))

    result = asyncio.run(provider.structure_course(REQUEST))

    assert result.result.clean_course == "# La cellule"
    assert (result.input_tokens, result.output_tokens) == (30, 12)
    [call] = completions.calls
    assert call["model"] == "qwen3:8b"
    assert call["response_format"] is StructureResult
    system, user = call["messages"]
    assert system["role"] == "system" and "ajouter silencieusement" in system["content"]
    assert "la cellule" in user["content"]


def test_photo_is_sent_as_image_url() -> None:
    provider, completions = make_provider(completion(PhotoResult(text="la cellule", uncertain=[])))
    request = PhotoRequest(
        subject="SVT", chapter="Cellule", image_data_url="data:image/jpeg;base64,AA"
    )

    assert asyncio.run(provider.transcribe_photo(request)).result.text == "la cellule"

    user = completions.calls[0]["messages"][1]["content"]
    assert user[0]["type"] == "text"
    assert user[1] == {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,AA"}}


@pytest.mark.parametrize(
    ("outcome", "code"),
    [
        (completion(None), "ai_invalid_response"),
        (SimpleNamespace(choices=[], usage=None), "ai_invalid_response"),
        (openai.APIConnectionError(request=HTTP_REQUEST), "ai_local_unavailable"),
        (
            openai.NotFoundError(
                "model not found", response=httpx.Response(404, request=HTTP_REQUEST), body=None
            ),
            "ai_local_model_missing",
        ),
    ],
)
def test_errors(outcome: Any, code: str) -> None:
    provider, _ = make_provider(outcome)
    with pytest.raises(AIProviderError) as error:
        asyncio.run(provider.structure_course(REQUEST))
    assert error.value.code == code


def test_factory_builds_local_provider_without_key() -> None:
    provider = build_ai_provider(
        Settings(_env_file=None, ai_provider="local", local_ai_base_url="http://ollama:11434/v1")
    )
    assert isinstance(provider, LocalProvider)
    assert provider.paid is False
    assert str(provider.client.base_url) == "http://ollama:11434/v1/"


def test_local_provider_ignores_ai_budget(settings: Settings) -> None:
    app = create_app(settings.model_copy(update={"ai_monthly_budget_eur": 0.0001}))
    with TestClient(app) as client:
        with app.state.db.session_factory() as session:
            session.add(
                AIRun(
                    operation="structure",
                    provider="openai",
                    model="m",
                    prompt_version="v",
                    input_hash="h",
                    estimated_cost_eur=1.0,
                    status="success",
                    duration_ms=1,
                )
            )
            session.commit()
        provider = app.state.ai_provider = build_ai_provider(settings)  # fake
        provider.paid = False
        subject_id = client.get("/api/subjects").json()[0]["id"]
        chapter_id = client.post(
            "/api/chapters", json={"subject_id": subject_id, "title": "T"}
        ).json()["id"]
        structured(client, chapter_id, "notes", "# Cours\n")
