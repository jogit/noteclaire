import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

from app.api import (
    auth,
    backups,
    chapters,
    chatgpt,
    images,
    photos,
    references,
    search,
    setup,
    students,
    study,
    subjects,
    suggestions,
    trash,
    usage,
)
from app.api.deps import SettingsDep, require_auth, require_owner
from app.auth import LoginThrottle
from app.config import Settings, get_settings
from app.database import Database
from app.errors import AppError
from app.services.ai_config import load_saved_config
from app.services.backup_service import run_scheduler
from app.services.chatgpt.oauth import ChatGPTAuth
from app.services.chatgpt.session import ChatGPTSession
from app.services.chatgpt.store import CredentialStore
from app.services.reference_service import sync_references
from app.services.search_service import reindex_all
from app.services.student_service import seed_default_student
from app.services.subject_service import seed_subjects
from app.services.trash_service import purge_expired

logger = logging.getLogger("app")


class RedactCallbackQuery(logging.Filter):
    """Retire le code d'autorisation et le state de l'URL de retour dans le log d'accès."""

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if isinstance(args, tuple) and len(args) >= 3 and isinstance(args[2], str):
            path = args[2]
            if path.startswith("/auth/callback?"):
                record.args = (*args[:2], "/auth/callback?[masqué]", *args[3:])
        return True


def _prepare_data(app: FastAPI, settings: Settings) -> None:
    """Au démarrage : données de départ, index des références et de la recherche, corbeille."""
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    load_saved_config(settings)
    with app.state.db.session_factory() as session:
        seed_subjects(session)
        seed_default_student(session)
        sync_references(session, settings)
        reindex_all(session)
        purged = purge_expired(session, settings)
        if purged:
            logger.info("corbeille : %d chapitre(s) effacé(s) après 30 jours", purged)


def _warn_about_config(settings: Settings) -> None:
    if settings.app_env == "production" and not settings.app_password:
        logger.warning("APP_PASSWORD est vide : application accessible sans mot de passe.")
    if settings.ai_provider == "openai" and not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY est vide : les fonctions IA sont désactivées.")


def _add_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
        )

    @app.exception_handler(OperationalError)
    async def db_error_handler(_request: Request, exc: OperationalError) -> JSONResponse:
        locked = "locked" in str(exc.orig)
        logger.error("database error locked=%s", locked)
        code, message = (
            ("db_locked", "La base de données est occupée. Réessaie dans un instant.")
            if locked
            else ("db_error", "Erreur de base de données.")
        )
        return JSONResponse(status_code=503, content={"error": {"code": code, "message": message}})


def _add_routers(app: FastAPI) -> None:
    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    protected = [Depends(require_auth), Depends(require_owner)]

    @app.get("/api/version", dependencies=protected)
    def version(settings: SettingsDep) -> dict[str, str]:
        return {"version": settings.app_version}

    app.include_router(auth.router)
    app.include_router(chatgpt.callback_router)  # public : protégé par le paramètre state
    for router in (
        chatgpt.router,
        setup.router,
        students.router,
        subjects.router,
        chapters.router,
        suggestions.router,
        usage.router,
        references.router,
        search.router,
        study.router,
        images.router,
        photos.router,
        trash.router,
        backups.router,
    ):
        app.include_router(router, dependencies=protected)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(level=settings.log_level.upper())
    access_log = logging.getLogger("uvicorn.access")
    if not any(isinstance(f, RedactCallbackQuery) for f in access_log.filters):
        access_log.addFilter(RedactCallbackQuery())

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        _prepare_data(app, settings)
        _warn_about_config(settings)
        scheduler = None
        if settings.backups_enabled and settings.app_env != "test":
            scheduler = asyncio.create_task(run_scheduler(settings, app.state.db.engine))
        yield
        if scheduler is not None:
            scheduler.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await scheduler

    app = FastAPI(title="NoteClaire", lifespan=lifespan)
    app.state.settings = settings
    app.state.db = Database(settings.database_url)
    app.state.ai_provider = None
    app.state.login_throttle = LoginThrottle()
    app.state.chatgpt = ChatGPTSession(
        CredentialStore(settings.data_dir),
        ChatGPTAuth(),
        settings.chatgpt_redirect_port,
        settings.chatgpt_model,
    )
    _add_error_handlers(app)
    _add_routers(app)
    return app
