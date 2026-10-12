from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from app.auth import SESSION_COOKIE, is_valid_token
from app.config import Settings
from app.errors import AppError, NotFoundError
from app.models import AISuggestion, Chapter, Student
from app.services.ai.base import AIProvider
from app.services.ai.factory import build_ai_provider
from app.services.student_service import resolve_student


def get_settings_dep(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_db(request: Request) -> Iterator[Session]:
    yield from request.app.state.db.session()


def get_ai_provider(request: Request) -> AIProvider:
    state = request.app.state
    if state.ai_provider is None:
        state.ai_provider = build_ai_provider(state.settings, state.chatgpt)
    provider: AIProvider = state.ai_provider
    return provider


STUDENT_COOKIE = "noteclaire_student"


def get_student(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    x_student_id: Annotated[int | None, Header()] = None,
) -> Student:
    """Élève courant, choisi dans le navigateur : en-tête X-Student-Id, sinon cookie.

    Le cookie sert aux requêtes que le navigateur envoie seul (images, photos, téléchargements).
    """
    if x_student_id is None:
        cookie = request.cookies.get(STUDENT_COOKIE, "")
        x_student_id = int(cookie) if cookie.isdecimal() else None
    return resolve_student(db, x_student_id)


SettingsDep = Annotated[Settings, Depends(get_settings_dep)]
DbDep = Annotated[Session, Depends(get_db)]
StudentDep = Annotated[Student, Depends(get_student)]
AIProviderDep = Annotated[AIProvider, Depends(get_ai_provider)]


def require_auth(request: Request, settings: SettingsDep) -> None:
    if not settings.app_password:
        return
    if not is_valid_token(settings.app_password, request.cookies.get(SESSION_COOKIE)):
        raise AppError("auth_required", "Connexion requise.", 401)


def require_owner(request: Request, db: DbDep, student: StudentDep) -> None:
    """Les chapitres (et leurs suggestions) ne sont accessibles qu'à l'élève à qui ils sont.

    S'applique à toute route dont l'adresse contient `chapter_id` ou `suggestion_id`.
    """
    params = request.path_params
    chapter_id = params.get("chapter_id")
    if chapter_id is None and "suggestion_id" in params:
        suggestion = db.get(AISuggestion, int(params["suggestion_id"]))
        if suggestion is None:
            raise NotFoundError("Cette suggestion n'existe pas.")
        chapter_id = suggestion.chapter_id
    if chapter_id is None:
        return
    chapter = db.get(Chapter, int(chapter_id))
    if chapter is None or chapter.student_id != student.id:
        raise NotFoundError("Ce chapitre n'existe pas.")
