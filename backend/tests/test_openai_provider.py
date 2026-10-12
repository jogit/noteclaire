"""Tests du provider OpenAI avec un client simulé : aucun appel réseau."""

import asyncio
from types import SimpleNamespace
from typing import Any, cast

import httpx2 as httpx  # client HTTP utilisé par le SDK openai
import openai
import pytest
from openai import AsyncOpenAI
from openai.lib._pydantic import to_strict_json_schema

from app.prompts import render_prompt
from app.services.ai.base import (
    AIProviderError,
    AnalyzeRequest,
    AnalyzeResult,
    ExplainResult,
    PhotoResult,
    QuizResult,
    RevisionSheetResult,
    StructureRequest,
    StructureResult,
)
from app.services.ai.openai_provider import OpenAIProvider

REQUEST = StructureRequest(subject="Mathématiques", chapter="Fonctions", raw_notes="f(x)=ax+b")
HTTP_REQUEST = httpx.Request("POST", "https://api.openai.com/v1/responses")


class FakeResponses:
    def __init__(self, outcome: Any) -> None:
        self.outcome = outcome
        self.calls: list[dict[str, Any]] = []

    async def parse(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


def make_provider(outcome: Any) -> tuple[OpenAIProvider, FakeResponses]:
    responses = FakeResponses(outcome)
    client = cast(AsyncOpenAI, SimpleNamespace(responses=responses))
    return OpenAIProvider(client, "gpt-test"), responses


def status_error(cls: type[openai.APIStatusError], code: str | None = None) -> Exception:
    response = httpx.Response(400, request=HTTP_REQUEST)
    body = {"code": code} if code else None  # le SDK passe le contenu de "error"
    return cls("erreur", response=response, body=body)


def test_structure_sends_prompt_and_parses_result() -> None:
    parsed = StructureResult(clean_course="# Fonctions\n\n$f(x) = ax + b$")
    usage = SimpleNamespace(input_tokens=10, output_tokens=5)
    provider, responses = make_provider(SimpleNamespace(output_parsed=parsed, usage=usage))

    result = asyncio.run(provider.structure_course(REQUEST))

    assert result.result.clean_course.startswith("# Fonctions")
    assert (result.input_tokens, result.output_tokens) == (10, 5)
    [call] = responses.calls
    assert call["model"] == "gpt-test"
    assert (
        call["store"] is False
    )  # rien n'est conservé côté OpenAI pour une consultation ultérieure
    assert call["text_format"] is StructureResult
    assert "f(x)=ax+b" in call["input"]
    assert "Mathématiques" in call["input"]
    assert "ajouter silencieusement" in call["instructions"]


@pytest.mark.parametrize(
    ("outcome", "code"),
    [
        (SimpleNamespace(output_parsed=None, usage=None), "ai_invalid_response"),
        (openai.APITimeoutError(request=HTTP_REQUEST), "ai_timeout"),
        (openai.APIConnectionError(request=HTTP_REQUEST), "ai_unavailable"),
        (status_error(openai.AuthenticationError), "ai_invalid_key"),
        (status_error(openai.RateLimitError, "insufficient_quota"), "ai_quota_exceeded"),
        (status_error(openai.RateLimitError), "ai_rate_limited"),
        (status_error(openai.InternalServerError), "ai_unavailable"),
    ],
)
def test_errors_are_mapped(outcome: Any, code: str) -> None:
    provider, _ = make_provider(outcome)
    with pytest.raises(AIProviderError) as error:
        asyncio.run(provider.structure_course(REQUEST))
    assert error.value.code == code


def test_empty_course_is_invalid() -> None:
    parsed = SimpleNamespace(model_dump=lambda: {"clean_course": ""})
    provider, _ = make_provider(SimpleNamespace(output_parsed=parsed, usage=None))
    with pytest.raises(AIProviderError) as error:
        asyncio.run(provider.structure_course(REQUEST))
    assert error.value.code == "ai_invalid_response"


def test_render_prompt_does_not_reinterpret_values() -> None:
    prompt = render_prompt("structure", subject="S", chapter="C", raw_notes="{{ subject }} $x$")
    assert "{{ subject }} $x$" in prompt
    assert "{{ raw_notes }}" not in prompt


def test_analyze_sends_course_and_parses_suggestions() -> None:
    parsed = AnalyzeResult.model_validate(
        {
            "suggestions": [
                {
                    "type": "correction",
                    "original_text": "b est la pente",
                    "suggested_text": "a est le coefficient directeur",
                    "reason": "Inversion.",
                    "confidence": 0.8,
                    "reference_title": "",
                }
            ]
        }
    )
    provider, responses = make_provider(SimpleNamespace(output_parsed=parsed, usage=None))
    request = AnalyzeRequest(
        subject="Mathématiques", chapter="Fonctions", course="# Cours", reference_context="Aucun"
    )

    result = asyncio.run(provider.analyze_course(request))

    assert result.result.suggestions[0].type == "correction"
    [call] = responses.calls
    assert call["text_format"] is AnalyzeResult
    assert "# Cours" in call["input"]
    assert "Aucun" in call["input"]


def test_schemas_only_use_keywords_supported_by_structured_outputs() -> None:
    for schema in (
        StructureResult,
        AnalyzeResult,
        RevisionSheetResult,
        QuizResult,
        ExplainResult,
        PhotoResult,
    ):
        text = str(to_strict_json_schema(schema))
        for keyword in ("minLength", "maxLength", "minimum", "maximum", "default"):
            assert keyword not in text, (schema.__name__, keyword)
