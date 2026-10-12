from fastapi import APIRouter

from app.api.chapters import course_out
from app.api.deps import DbDep
from app.schemas.api import AcceptIn, AcceptOut, SuggestionOut
from app.services import suggestion_service

router = APIRouter(prefix="/api/suggestions", tags=["suggestions"])


@router.post("/{suggestion_id}/accept")
def accept(suggestion_id: int, db: DbDep, data: AcceptIn | None = None) -> AcceptOut:
    occurrence = data.occurrence if data else None
    result = suggestion_service.accept_suggestion(db, suggestion_id, occurrence)
    return AcceptOut(
        suggestion=SuggestionOut.model_validate(result.suggestion),
        course=course_out(db, result.course),
    )


@router.post("/{suggestion_id}/reject")
def reject(suggestion_id: int, db: DbDep) -> SuggestionOut:
    return SuggestionOut.model_validate(suggestion_service.reject_suggestion(db, suggestion_id))
