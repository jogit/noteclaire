"""Exécution journalisée des appels IA : budget, nouvelle tentative, AIRun (SPEC §9, §29)."""

import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.errors import AppError
from app.models import AIRun, Chapter
from app.services.ai.base import AIProviderError, AIResponse

logger = logging.getLogger(__name__)


def estimate_cost(
    settings: Settings, input_tokens: int | None, output_tokens: int | None
) -> float | None:
    input_price = settings.ai_input_price_eur_per_mtok
    output_price = settings.ai_output_price_eur_per_mtok
    if input_price is None or output_price is None or input_tokens is None or output_tokens is None:
        return None
    return (input_tokens * input_price + output_tokens * output_price) / 1_000_000


def month_cost(db: Session) -> float:
    now = datetime.now(UTC)
    month_start = datetime(now.year, now.month, 1)  # dates stockées en UTC sans fuseau
    total = db.scalar(
        select(func.sum(AIRun.estimated_cost_eur)).where(AIRun.created_at >= month_start)
    )
    return float(total or 0)


@dataclass(frozen=True)
class OperationUsage:
    operation: str
    calls: int
    errors: int
    input_tokens: int
    output_tokens: int
    cost_eur: float


@dataclass(frozen=True)
class RecentRun:
    created_at: datetime
    operation: str
    chapter_title: str
    provider: str
    model: str
    status: str
    error_code: str
    input_tokens: int
    output_tokens: int
    duration_ms: int


def usage_by_operation(db: Session, since: datetime) -> list[OperationUsage]:
    """Appels et tokens par opération depuis une date (UTC, sans fuseau)."""
    rows = db.execute(
        select(
            AIRun.operation,
            func.count(),
            func.sum(case((AIRun.status == "error", 1), else_=0)),
            func.coalesce(func.sum(AIRun.input_tokens), 0),
            func.coalesce(func.sum(AIRun.output_tokens), 0),
            func.coalesce(func.sum(AIRun.estimated_cost_eur), 0.0),
        )
        .where(AIRun.created_at >= since)
        .group_by(AIRun.operation)
        .order_by(func.count().desc())
    ).all()
    return [
        OperationUsage(op, int(calls), int(errors or 0), int(tin), int(tout), float(cost))
        for op, calls, errors, tin, tout, cost in rows
    ]


def recent_runs(db: Session, student_id: int, limit: int = 20) -> list[RecentRun]:
    """Derniers appels IA sur les chapitres de l'élève (ceux des autres restent privés)."""
    rows = db.execute(
        select(AIRun, Chapter.title)
        .join(Chapter, Chapter.id == AIRun.chapter_id)
        .where(Chapter.student_id == student_id)
        .order_by(AIRun.created_at.desc(), AIRun.id.desc())
        .limit(limit)
    ).all()
    return [
        RecentRun(
            created_at=run.created_at,
            operation=run.operation,
            chapter_title=title or "",
            provider=run.provider,
            model=run.model,
            status=run.status,
            error_code=run.error_code or "",
            input_tokens=run.input_tokens or 0,
            output_tokens=run.output_tokens or 0,
            duration_ms=run.duration_ms,
        )
        for run, title in rows
    ]


# Durées par défaut (secondes), tant qu'il n'y a pas d'appel réussi à mesurer.
DEFAULT_DURATIONS = {
    "structure": 20.0,
    "analyze": 30.0,
    "revision_sheet": 25.0,
    "quiz": 20.0,
    "explain": 10.0,
    "photo": 15.0,
    "figures": 12.0,
    "redraw": 25.0,
}


def typical_durations(db: Session, provider: str, sample: int = 10) -> dict[str, float]:
    """Durée habituelle de chaque opération (médiane des derniers appels réussis), en secondes.

    Sert à afficher une progression estimée : l'IA ne dit pas où elle en est.
    """
    durations = dict(DEFAULT_DURATIONS)
    for operation in DEFAULT_DURATIONS:
        recent = list(
            db.scalars(
                select(AIRun.duration_ms)
                .where(
                    AIRun.operation == operation,
                    AIRun.provider == provider,
                    AIRun.status == "success",
                )
                .order_by(AIRun.created_at.desc())
                .limit(sample)
            )
        )
        if recent:
            recent.sort()
            middle = len(recent) // 2
            median = (
                recent[middle] if len(recent) % 2 else (recent[middle - 1] + recent[middle]) / 2
            )
            durations[operation] = round(median / 1000, 1)
    return durations


def check_budget(db: Session, settings: Settings) -> None:
    budget = settings.ai_monthly_budget_eur
    if budget > 0 and month_cost(db) >= budget:
        raise AppError(
            "ai_budget_exceeded",
            "Le budget IA du mois est atteint. Les fonctions IA reviendront le mois prochain.",
            429,
        )


async def run_ai[T](
    db: Session,
    settings: Settings,
    call: Callable[[], Awaitable[AIResponse[T]]],
    *,
    chapter_id: int | None,
    operation: str,
    provider: str,
    model: str,
    prompt_version: str,
    input_hash: str,
    enforce_budget: bool = True,
) -> tuple[AIResponse[T], AIRun]:
    """Appelle l'IA et journalise chaque tentative dans AIRun.

    Une seule nouvelle tentative si la réponse est invalide. Le contenu n'est jamais loggé.
    """
    if enforce_budget:
        check_budget(db, settings)
    for attempt in (1, 2):
        started = time.perf_counter()
        run = AIRun(
            chapter_id=chapter_id,
            operation=operation,
            provider=provider,
            model=model,
            prompt_version=prompt_version,
            input_hash=input_hash,
        )
        try:
            response = await call()
        except AIProviderError as exc:
            _finish(db, run, started, status="error", error_code=exc.code)
            db.commit()
            logger.warning(
                "%s chapter=%s attempt=%s error=%s", operation, chapter_id, attempt, exc.code
            )
            if exc.code == "ai_invalid_response" and attempt == 1:
                continue
            raise

        run.input_tokens = response.input_tokens
        run.output_tokens = response.output_tokens
        # Un provider gratuit ou inclus dans un abonnement n'a pas de coût en euros.
        if enforce_budget:
            run.estimated_cost_eur = estimate_cost(
                settings, response.input_tokens, response.output_tokens
            )
        _finish(db, run, started, status="success")
        db.flush()
        logger.info("%s chapter=%s ok duration_ms=%s", operation, chapter_id, run.duration_ms)
        return response, run

    raise AssertionError("unreachable")


def _finish(
    db: Session, run: AIRun, started: float, status: str, error_code: str | None = None
) -> None:
    run.status = status
    run.error_code = error_code
    run.duration_ms = int((time.perf_counter() - started) * 1000)
    db.add(run)
