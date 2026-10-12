from typing import Any, cast

import openai
from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from app.prompts import load_prompt
from app.services.ai.base import AIProviderError, AIResponse
from app.services.ai.openai_errors import map_openai_error
from app.services.ai.prompted import PromptedProvider


class OpenAIProvider(PromptedProvider):
    """API OpenAI (Responses API + structured outputs)."""

    name = "openai"

    def __init__(self, client: AsyncOpenAI, model: str) -> None:
        self.client = client
        self.model = model

    async def _parse[T: BaseModel](
        self, prompt: str, schema: type[T], images: tuple[str, ...] = ()
    ) -> AIResponse[T]:
        try:
            response = await self.client.responses.parse(
                model=self.model,
                instructions=load_prompt("system"),
                input=cast(Any, responses_input(prompt, images) if images else prompt),
                text_format=schema,
                store=False,  # pas de conservation côté OpenAI pour une consultation ultérieure
            )
        except (ValidationError, openai.LengthFinishReasonError) as exc:
            raise AIProviderError("ai_invalid_response") from exc
        except openai.OpenAIError as exc:
            raise map_openai_error(exc) from exc

        usage = response.usage
        return AIResponse(
            result=revalidate(response.output_parsed, schema),
            input_tokens=usage.input_tokens if usage else None,
            output_tokens=usage.output_tokens if usage else None,
        )


def responses_input(prompt: str, images: tuple[str, ...]) -> list[dict[str, Any]]:
    """Message utilisateur de la Responses API : texte puis images (data URL)."""
    content: list[dict[str, Any]] = [{"type": "input_text", "text": prompt}]
    content += [{"type": "input_image", "image_url": url, "detail": "high"} for url in images]
    return [{"role": "user", "content": content}]


def revalidate[T: BaseModel](parsed: BaseModel | None, schema: type[T]) -> T:
    """Le schéma est contraint côté serveur, mais on revalide quand même."""
    if parsed is None:
        raise AIProviderError("ai_invalid_response")
    try:
        return schema.model_validate(parsed.model_dump())
    except ValidationError as exc:
        raise AIProviderError("ai_invalid_response") from exc
