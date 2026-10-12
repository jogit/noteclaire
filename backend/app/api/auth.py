import asyncio

from fastapi import APIRouter, Request, Response

from app.api.deps import SettingsDep
from app.auth import (
    SESSION_COOKIE,
    SESSION_LIFETIME_SECONDS,
    is_valid_password,
    is_valid_token,
    session_token,
)
from app.errors import AppError
from app.schemas.api import AuthStatus, LoginIn

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/status")
def status(request: Request, settings: SettingsDep) -> AuthStatus:
    if not settings.app_password:
        return AuthStatus(auth_required=False, authenticated=True)
    token = request.cookies.get(SESSION_COOKIE)
    return AuthStatus(
        auth_required=True, authenticated=is_valid_token(settings.app_password, token)
    )


@router.post("/login", status_code=204)
async def login(data: LoginIn, request: Request, response: Response, settings: SettingsDep) -> None:
    if not settings.app_password:
        return
    throttle = request.app.state.login_throttle
    client = request.client.host if request.client else ""
    if throttle.blocked(client):
        raise AppError("auth_throttled", "Trop d'essais. Réessaie dans quelques minutes.", 429)
    if not is_valid_password(settings.app_password, data.password):
        throttle.failed(client)
        await asyncio.sleep(1)  # ralentit les essais en série
        raise AppError("auth_invalid", "Mot de passe incorrect.", 401)
    throttle.succeeded(client)
    response.set_cookie(
        SESSION_COOKIE,
        session_token(settings.app_password),
        max_age=SESSION_LIFETIME_SECONDS,
        httponly=True,
        samesite="strict",
        secure=request.url.scheme == "https",
    )


@router.post("/logout", status_code=204)
def logout(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE)
