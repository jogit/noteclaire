import openai

from app.services.ai.base import AIProviderError


def map_openai_error(exc: openai.OpenAIError) -> AIProviderError:
    # APITimeoutError hérite de APIConnectionError : le tester en premier.
    if isinstance(exc, openai.APITimeoutError):
        return AIProviderError("ai_timeout")
    if isinstance(exc, openai.APIConnectionError):
        return AIProviderError("ai_unavailable")
    if isinstance(exc, openai.AuthenticationError | openai.PermissionDeniedError):
        return AIProviderError("ai_invalid_key")
    if isinstance(exc, openai.RateLimitError):
        if getattr(exc, "code", None) == "insufficient_quota":
            return AIProviderError("ai_quota_exceeded")
        return AIProviderError("ai_rate_limited")
    return AIProviderError("ai_unavailable")
