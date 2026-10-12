from dataclasses import asdict
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter

from app.api.deps import DbDep, SettingsDep, StudentDep
from app.schemas.api import OperationUsageOut, RecentRunOut, UsageDetailsOut, UsageOut
from app.services.ai_runs import month_cost, recent_runs, typical_durations, usage_by_operation

# Page officielle de suivi et de limitation de l'usage de l'abonnement (SDK officiel).
CHATGPT_USAGE_URL = "https://chatgpt.com/settings/usage"

router = APIRouter(prefix="/api/usage", tags=["usage"])


@router.get("")
def usage(db: DbDep, settings: SettingsDep) -> UsageOut:
    return UsageOut(
        month_cost_eur=round(month_cost(db), 4),
        budget_eur=settings.ai_monthly_budget_eur,
        cost_tracking=settings.ai_input_price_eur_per_mtok is not None
        and settings.ai_output_price_eur_per_mtok is not None,
    )


@router.get("/details")
def details(db: DbDep, settings: SettingsDep, student: StudentDep) -> UsageDetailsOut:
    """Consommation enregistrée par NoteClaire (journal AIRun). L'abonnement ChatGPT
    n'expose pas sa jauge : elle se consulte sur chatgpt.com."""
    now = datetime.now(UTC).replace(tzinfo=None)  # dates stockées en UTC sans fuseau
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    def rows(since: datetime) -> list[OperationUsageOut]:
        return [OperationUsageOut(**asdict(u)) for u in usage_by_operation(db, since)]

    return UsageDetailsOut(
        ai_provider=settings.ai_provider,
        last_7_days=rows(now - timedelta(days=7)),
        this_month=rows(month_start),
        recent=[RecentRunOut(**asdict(r)) for r in recent_runs(db, student.id)],
        chatgpt_usage_url=CHATGPT_USAGE_URL,
    )


@router.get("/durations")
def durations(db: DbDep, settings: SettingsDep) -> dict[str, float]:
    """Durée habituelle de chaque opération IA (secondes), pour la barre de progression."""
    return typical_durations(db, settings.ai_provider)
