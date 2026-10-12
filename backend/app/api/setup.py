from fastapi import APIRouter, Request

from app.api.deps import SettingsDep
from app.schemas.api import AIConfigIn, SetupStatusOut, TestResultOut
from app.services import ai_config

router = APIRouter(prefix="/api/setup", tags=["setup"])


def _status(request: Request, settings: SettingsDep) -> SetupStatusOut:
    chatgpt = request.app.state.chatgpt
    ready = ai_config.is_ready(settings, chatgpt)
    return SetupStatusOut(
        needs_setup=not ready,
        ai_provider=settings.ai_provider,
        has_openai_key=bool(settings.openai_api_key),
        local_ai_base_url=settings.local_ai_base_url,
        local_ai_model=settings.local_ai_model,
        chatgpt_connected=chatgpt.status().connected,
    )


@router.get("/status")
def status(request: Request, settings: SettingsDep) -> SetupStatusOut:
    return _status(request, settings)


@router.put("/ai")
def save_ai(data: AIConfigIn, request: Request, settings: SettingsDep) -> SetupStatusOut:
    ai_config.save_config(settings, ai_config.AIConfig(**data.model_dump()))
    request.app.state.ai_provider = None  # reconstruit avec la nouvelle configuration
    return _status(request, settings)


@router.post("/ai/test")
async def test_ai(settings: SettingsDep) -> TestResultOut:
    ok, message = await ai_config.check_connection(settings)
    return TestResultOut(ok=ok, message=message)
