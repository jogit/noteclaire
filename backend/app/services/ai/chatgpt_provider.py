"""IA via l'abonnement ChatGPT de l'utilisateur (« Sign in with ChatGPT »).

Même API Responses qu'avec une clé, mais avec le jeton OAuth du compte, en flux continu
et `store: false`. Si le format imposé (structured outputs) n'est pas accepté par cette
voie, on bascule sur une consigne JSON dans le prompt ; la réponse est validée pareil.
"""

import json
import logging
import re
from collections.abc import Callable
from typing import Any

import openai
from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from app.prompts import load_prompt
from app.services.ai.base import AIProviderError, AIResponse
from app.services.ai.openai_errors import map_openai_error
from app.services.ai.openai_provider import responses_input
from app.services.ai.prompted import PromptedProvider
from app.services.chatgpt.oauth import RESOURCE, ChatGPTAuthError
from app.services.chatgpt.session import ChatGPTSession

ERROR_CODES = {
    "subscription_sharing_usage_limit_exceeded": "chatgpt_usage_limit",
    "subscription_sharing_user_not_eligible": "chatgpt_not_eligible",
    "subscription_sharing_v2_user_not_eligible": "chatgpt_not_eligible",
    "subscription_sharing_invalid_user": "chatgpt_not_eligible",
    "model_not_found": "chatgpt_model_unavailable",
}
UNSUPPORTED = {
    "subscription_sharing_unsupported_capability",
    "subscription_sharing_route_not_supported",
}

JSON_INSTRUCTIONS = """

FORMAT DE RÉPONSE
Réponds uniquement avec un objet JSON valide, sans texte autour, conforme à ce schéma :
{schema}"""


logger = logging.getLogger(__name__)


class _StructuredUnsupported(Exception):
    pass


def default_client_factory(timeout: float) -> Callable[[str], AsyncOpenAI]:
    def factory(token: str) -> AsyncOpenAI:
        return AsyncOpenAI(api_key=token, base_url=RESOURCE, timeout=timeout, max_retries=0)

    return factory


def parse_json_text[T: BaseModel](text: str, schema: type[T]) -> T:
    """Extrait l'objet JSON d'une réponse texte (éventuellement entourée de ```json)."""
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end < start:
        raise AIProviderError("ai_invalid_response")
    try:
        return schema.model_validate_json(cleaned[start : end + 1])
    except ValidationError as exc:
        raise AIProviderError("ai_invalid_response") from exc


class ChatGPTProvider(PromptedProvider):
    name = "chatgpt"
    paid = False  # inclus dans l'abonnement : pas de budget en euros

    def __init__(
        self, session: ChatGPTSession, client_factory: Callable[[str], AsyncOpenAI]
    ) -> None:
        self.session = session
        self.client_factory = client_factory
        self.structured = True

    @property
    def model(self) -> str:  # type: ignore[override]  # le modèle se choisit dans les Réglages
        return self.session.current_model()

    async def _parse[T: BaseModel](
        self, prompt: str, schema: type[T], images: tuple[str, ...] = ()
    ) -> AIResponse[T]:
        try:
            token = await self.session.access_token()
            model = await self.session.resolve_model()
        except ChatGPTAuthError as exc:
            raise _auth_error(exc) from exc
        client = self.client_factory(token)
        if self.structured:
            try:
                return await self._request(client, model, prompt, schema, images, structured=True)
            except _StructuredUnsupported:
                self.structured = False  # mémorisé pour les appels suivants
        return await self._request(client, model, prompt, schema, images, structured=False)

    @staticmethod
    def _call_arguments(
        model: str, prompt: str, schema: type[BaseModel], images: tuple[str, ...], structured: bool
    ) -> dict[str, Any]:
        instructions = load_prompt("system")
        # Cette voie exige une liste de messages (« Input must be a list »), pas une chaîne.
        arguments: dict[str, Any] = {
            "model": model,
            "input": responses_input(prompt, images)
            if images
            else [{"role": "user", "content": prompt}],
            "store": False,
        }
        if structured:
            arguments["text_format"] = schema
        else:
            instructions += JSON_INSTRUCTIONS.format(
                schema=json.dumps(schema.model_json_schema(), ensure_ascii=False)
            )
        return {"instructions": instructions, **arguments}

    @staticmethod
    async def _read_stream(
        client: AsyncOpenAI, arguments: dict[str, Any]
    ) -> tuple[str | None, list[str], Any]:
        """Lit le flux : (texte final, morceaux reçus, réponse terminée).

        L'événement final de cette voie ne contient pas la réponse (output vide) :
        comme le SDK officiel, on assemble le texte diffusé et on exige la fin du flux.
        """
        deltas: list[str] = []
        text: str | None = None
        completed: Any = None
        async with client.responses.stream(**arguments) as stream:
            async for event in stream:
                if event.type == "response.output_text.delta":
                    deltas.append(event.delta)
                elif event.type == "response.output_text.done":
                    text = event.text
                elif event.type == "response.completed":
                    completed = event.response
                elif event.type in {"response.failed", "response.incomplete", "error"}:
                    logger.warning("chatgpt stream ended event=%s", event.type)
                    raise AIProviderError(
                        "ai_invalid_response"
                        if event.type == "response.incomplete"
                        else "ai_unavailable"
                    )
        return text, deltas, completed

    async def _request[T: BaseModel](
        self,
        client: AsyncOpenAI,
        model: str,
        prompt: str,
        schema: type[T],
        images: tuple[str, ...],
        structured: bool,
    ) -> AIResponse[T]:
        arguments = self._call_arguments(model, prompt, schema, images, structured)
        try:
            text, deltas, completed = await self._read_stream(client, arguments)
        except (ValidationError, openai.LengthFinishReasonError) as exc:
            raise AIProviderError("ai_invalid_response") from exc
        except openai.APIStatusError as exc:
            raise _status_error(exc, structured) from exc
        except openai.OpenAIError as exc:
            raise map_openai_error(exc) from exc

        if completed is None:
            logger.warning("chatgpt stream interrupted before response.completed")
            raise AIProviderError("ai_invalid_response")
        result = parse_json_text(text if text is not None else "".join(deltas), schema)
        usage = getattr(completed, "usage", None)
        return AIResponse(
            result=result,
            input_tokens=usage.input_tokens if usage else None,
            output_tokens=usage.output_tokens if usage else None,
        )


def _status_error(exc: openai.APIStatusError, structured: bool) -> Exception:
    code = str(exc.code or "")
    # Message d'erreur du serveur (jamais le contenu du cours) : indispensable au diagnostic.
    logger.warning(
        "chatgpt responses error status=%s code=%s detail=%s",
        exc.status_code,
        code or "-",
        _detail(exc),
    )
    param = str(getattr(exc, "param", "") or "")
    if structured and (
        code in UNSUPPORTED or (exc.status_code == 400 and param.startswith("text"))
    ):
        return _StructuredUnsupported()
    if code in ERROR_CODES:
        return AIProviderError(ERROR_CODES[code])
    if exc.status_code == 401:
        return AIProviderError("chatgpt_reauth")
    return map_openai_error(exc)


def _detail(exc: openai.APIStatusError) -> str:
    body = exc.body
    if isinstance(body, dict):
        detail = body.get("detail") or body.get("message") or ""
        return str(detail)[:200]
    return ""


def _auth_error(exc: ChatGPTAuthError) -> AIProviderError:
    if exc.code in AIProviderError.MESSAGES:
        return AIProviderError(exc.code)
    return AIProviderError("chatgpt_auth_unavailable" if exc.retryable else "chatgpt_reauth")
