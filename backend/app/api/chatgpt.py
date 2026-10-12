import logging

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.api.deps import SettingsDep
from app.errors import AppError
from app.schemas.api import (
    ChatGPTLoginOut,
    ChatGPTLogoutOut,
    ChatGPTModelIn,
    ChatGPTModelOut,
    ChatGPTStatusOut,
)
from app.services.chatgpt.oauth import CALLBACK_PATH, ChatGPTAuthError
from app.services.chatgpt.session import ChatGPTSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chatgpt", tags=["chatgpt"])
callback_router = APIRouter(tags=["chatgpt"])


def session(request: Request) -> ChatGPTSession:
    chatgpt: ChatGPTSession = request.app.state.chatgpt
    return chatgpt


def app_error(exc: ChatGPTAuthError) -> AppError:
    return AppError(exc.code, exc.message, 503 if exc.retryable else 409)


@router.get("/status")
def status(request: Request, settings: SettingsDep) -> ChatGPTStatusOut:
    chatgpt = session(request)
    current = chatgpt.status()
    return ChatGPTStatusOut(
        ai_provider=settings.ai_provider,
        connected=current.connected,
        email=current.email,
        name=current.name,
        model=current.model,
        needs_reauth=current.needs_reauth,
        redirect_uri=chatgpt.redirect_uri,
    )


@router.post("/login")
async def login(request: Request) -> ChatGPTLoginOut:
    try:
        return ChatGPTLoginOut(authorization_url=await session(request).start_login())
    except ChatGPTAuthError as exc:
        raise app_error(exc) from exc


@router.get("/models")
async def models(request: Request) -> list[ChatGPTModelOut]:
    try:
        found = await session(request).list_models()
    except ChatGPTAuthError as exc:
        raise app_error(exc) from exc
    return [ChatGPTModelOut(slug=m.slug, display_name=m.display_name) for m in found]


@router.put("/model", status_code=204)
async def set_model(data: ChatGPTModelIn, request: Request) -> None:
    try:
        await session(request).set_model(data.model)
    except ChatGPTAuthError as exc:
        raise app_error(exc) from exc


@router.post("/logout")
async def logout(request: Request) -> ChatGPTLogoutOut:
    return ChatGPTLogoutOut(revoked=await session(request).disconnect())


@callback_router.get(CALLBACK_PATH)
async def callback(request: Request) -> RedirectResponse:
    """Retour du navigateur après la connexion sur chatgpt.com."""
    params = dict(request.query_params)
    if any(len(request.query_params.getlist(k)) > 1 for k in ("state", "code", "client_id")):
        params = {"error": "invalid_request"}
    try:
        await session(request).finish_login(params)
    except ChatGPTAuthError as exc:
        logger.warning("chatgpt callback error=%s", exc.code)
        return RedirectResponse(f"/reglages?chatgpt=erreur&code={exc.code}", status_code=303)
    return RedirectResponse("/reglages?chatgpt=connecte", status_code=303)
