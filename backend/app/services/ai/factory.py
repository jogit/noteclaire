from openai import AsyncOpenAI

from app.config import Settings
from app.services.ai.base import AIProvider, AIProviderError
from app.services.ai.chatgpt_provider import ChatGPTProvider, default_client_factory
from app.services.ai.fake_provider import FakeProvider
from app.services.ai.local_provider import LocalProvider
from app.services.ai.openai_provider import OpenAIProvider
from app.services.chatgpt.session import ChatGPTSession


def _openai_client(settings: Settings) -> AsyncOpenAI:
    if not settings.openai_api_key:
        raise AIProviderError("ai_not_configured")
    return AsyncOpenAI(
        api_key=settings.openai_api_key,
        timeout=settings.ai_timeout_seconds,
        max_retries=1,
    )


def build_ai_provider(settings: Settings, chatgpt: ChatGPTSession | None = None) -> AIProvider:
    if settings.ai_provider == "fake":
        return FakeProvider()
    if settings.ai_provider == "chatgpt":
        if chatgpt is None:
            raise AIProviderError("chatgpt_not_connected")
        return ChatGPTProvider(chatgpt, default_client_factory(settings.ai_timeout_seconds))
    if settings.ai_provider == "local":
        client = AsyncOpenAI(
            api_key=settings.local_ai_api_key or "local",
            base_url=settings.local_ai_base_url,
            timeout=settings.local_ai_timeout_seconds,
            max_retries=0,
        )
        return LocalProvider(client, settings.local_ai_model)
    return OpenAIProvider(_openai_client(settings), settings.openai_model)
