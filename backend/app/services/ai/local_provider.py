from typing import Any

import openai
from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from app.prompts import load_prompt
from app.services.ai.base import AIProviderError, AIResponse
from app.services.ai.openai_errors import map_openai_error
from app.services.ai.openai_provider import revalidate
from app.services.ai.prompted import PromptedProvider


class LocalProvider(PromptedProvider):
    """Modèle local via une API compatible OpenAI : Ollama, LM Studio, llama.cpp…

    Utilise Chat Completions avec `response_format` (schéma JSON), pris en charge par ces
    serveurs, plutôt que la Responses API. Gratuit : non soumis au budget IA.
    """

    name = "local"
    paid = False

    def __init__(self, client: AsyncOpenAI, model: str) -> None:
        self.client = client
        self.model = model

    async def _parse[T: BaseModel](
        self, prompt: str, schema: type[T], images: tuple[str, ...] = ()
    ) -> AIResponse[T]:
        user: Any = prompt
        if images:  # le modèle local doit savoir lire les images (ex. qwen2.5-vl)
            user = [{"type": "text", "text": prompt}] + [
                {"type": "image_url", "image_url": {"url": url}} for url in images
            ]
        try:
            completion = await self.client.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": load_prompt("system")},
                    {"role": "user", "content": user},
                ],
                response_format=schema,
            )
        except (ValidationError, openai.LengthFinishReasonError) as exc:
            raise AIProviderError("ai_invalid_response") from exc
        except TypeError as exc:  # serveur ayant répondu une erreur au lieu d'une complétion
            raise AIProviderError("ai_invalid_response") from exc
        except openai.APIConnectionError as exc:
            raise AIProviderError("ai_local_unavailable") from exc
        except openai.OpenAIError as exc:
            if isinstance(exc, openai.NotFoundError):
                raise AIProviderError("ai_local_model_missing") from exc
            raise map_openai_error(exc) from exc

        if not completion.choices:
            raise AIProviderError("ai_invalid_response")
        usage = completion.usage
        return AIResponse(
            result=revalidate(completion.choices[0].message.parsed, schema),
            input_tokens=usage.prompt_tokens if usage else None,
            output_tokens=usage.completion_tokens if usage else None,
        )
