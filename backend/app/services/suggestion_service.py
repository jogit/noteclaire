"""Analyse du cours et application des suggestions (SPEC §13, §18.1)."""

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.errors import AppError, NotFoundError
from app.levels import adaptations_text, prompt_label
from app.models import AISuggestion, Chapter, Course
from app.models.entities import utcnow
from app.prompts import ANALYZE_PROMPT_VERSION
from app.services.ai.base import AIProvider, AnalyzeRequest, SuggestionItem
from app.services.ai_runs import run_ai
from app.services.chapter_service import get_chapter
from app.services.course_insert import insert_addition
from app.services.course_service import create_version, require_current_course, sha256
from app.services.reference_search import format_context, search_references

logger = logging.getLogger(__name__)

NO_REFERENCES = "Aucun document de référence n'est disponible pour cette matière."

MAX_SUGGESTIONS = 4
# Du plus important au moins important.
PRIORITY = ["correction", "warning", "missing_information", "clarification", "addition"]
REPLACING_TYPES = {"correction", "clarification", "missing_information"}
CONTEXT_CHARS = 40


@dataclass(frozen=True)
class AcceptResult:
    suggestion: AISuggestion
    course: Course


def _build_request(
    db: Session, chapter: Chapter, course: Course, rejected: list[AISuggestion]
) -> tuple[AnalyzeRequest, str]:
    """La demande d'analyse, et le contexte de référence qui l'accompagne."""
    excerpts = search_references(
        db, chapter.subject_id, chapter.student.level, f"{chapter.title}\n{course.content_markdown}"
    )
    context = format_context(excerpts)
    request = AnalyzeRequest(
        subject=chapter.subject.name,
        chapter=chapter.title,
        course=course.content_markdown,
        reference_context=context or NO_REFERENCES,
        reference_titles=tuple(dict.fromkeys(e.document_title for e in excerpts)),
        rejected=_format_rejected(rejected),
        level=prompt_label(chapter.student.level),
        adaptations=adaptations_text(
            chapter.student.adaptation_codes, chapter.student.adaptation_notes
        ),
    )
    return request, context


def _usable_items(
    items: list[SuggestionItem], course: Course, rejected: list[AISuggestion]
) -> list[SuggestionItem]:
    refused = {_key(r.original_text, r.suggested_text) for r in rejected}
    usable = [
        i
        for i in items
        if _is_usable(i, course.content_markdown)
        # Filet de sécurité : une suggestion refusée qui revient à l'identique est écartée.
        and _key(i.original_text, i.suggested_text) not in refused
    ]
    # Filet de sécurité : l'élève ne reçoit jamais plus de MAX_SUGGESTIONS points, les plus
    # importants d'abord (le tri est stable : l'ordre de l'IA est gardé à importance égale).
    return sorted(usable, key=lambda i: PRIORITY.index(i.type))[:MAX_SUGGESTIONS]


def _to_suggestions(
    items: list[SuggestionItem], course: Course, run_id: int, reference_titles: tuple[str, ...]
) -> list[AISuggestion]:
    return [
        AISuggestion(
            chapter_id=course.chapter_id,
            course_version_id=course.id,
            type=item.type,
            original_text=item.original_text,
            suggested_text=item.suggested_text,
            reason=item.reason,
            confidence=item.confidence,
            status="pending",
            ai_run_id=run_id,
            # Une source citée mais non fournie est ignorée : l'IA ne doit pas l'inventer.
            source_reference=item.reference_title
            if item.reference_title in reference_titles
            else "",
        )
        for item in items
    ]


async def analyze_chapter(
    db: Session, settings: Settings, chapter_id: int, provider: AIProvider
) -> list[AISuggestion]:
    """Analyse le cours courant et enregistre les suggestions. Le cours n'est pas modifié."""
    chapter = get_chapter(db, chapter_id)
    course = require_current_course(db, chapter_id)
    rejected = _rejected(db, chapter_id)
    request, context = _build_request(db, chapter, course, rejected)
    input_hash = sha256(
        "\n".join(
            [
                ANALYZE_PROMPT_VERSION,
                request.subject,
                request.level,
                request.chapter,
                request.course,
                context,
                request.rejected,
                request.adaptations,
            ]
        )
    )
    response, run = await run_ai(
        db,
        settings,
        lambda: provider.analyze_course(request),
        chapter_id=chapter_id,
        operation="analyze",
        provider=provider.name,
        model=provider.model,
        prompt_version=ANALYZE_PROMPT_VERSION,
        enforce_budget=provider.paid,
        input_hash=input_hash,
    )

    items = _usable_items(response.result.suggestions, course, rejected)
    discarded = len(response.result.suggestions) - len(items)
    if discarded:
        logger.info("analyze chapter=%s discarded=%s", chapter_id, discarded)

    # Une nouvelle analyse remplace les suggestions encore en attente.
    for old in _pending(db, chapter_id):
        old.status = "outdated"

    suggestions = _to_suggestions(items, course, run.id, request.reference_titles)
    db.add_all(suggestions)
    db.commit()
    return suggestions


def _is_usable(item: SuggestionItem, content: str) -> bool:
    if item.original_text:
        # L'IA doit citer un extrait exact : sinon la suggestion est inapplicable.
        if item.original_text not in content:
            return False
    elif item.type not in {"addition", "warning"}:
        return False
    if item.type == "warning":
        return True
    return bool(item.suggested_text.strip()) and item.suggested_text != item.original_text


MAX_REJECTED_IN_PROMPT = 30


def _rejected(db: Session, chapter_id: int) -> list[AISuggestion]:
    return list(
        db.scalars(
            select(AISuggestion)
            .where(AISuggestion.chapter_id == chapter_id, AISuggestion.status == "rejected")
            .order_by(AISuggestion.decided_at.desc())
            .limit(MAX_REJECTED_IN_PROMPT)
        )
    )


def _format_rejected(rejected: list[AISuggestion]) -> str:
    def short(text: str) -> str:
        flat = " ".join(text.split())
        return flat if len(flat) <= 200 else flat[:200] + "…"

    return "\n".join(
        f"- ({s.type}) « {short(s.original_text)} » → « {short(s.suggested_text)} »"
        for s in rejected
    )


def _key(original: str, suggested: str) -> tuple[str, str]:
    """Clé de comparaison insensible aux espaces et à la casse."""
    return (" ".join(original.split()).lower(), " ".join(suggested.split()).lower())


def _pending(db: Session, chapter_id: int) -> list[AISuggestion]:
    return list(
        db.scalars(
            select(AISuggestion).where(
                AISuggestion.chapter_id == chapter_id, AISuggestion.status == "pending"
            )
        )
    )


def list_suggestions(db: Session, chapter_id: int, status: str | None) -> list[AISuggestion]:
    get_chapter(db, chapter_id)
    query = select(AISuggestion).where(AISuggestion.chapter_id == chapter_id)
    if status:
        query = query.where(AISuggestion.status == status)
    return list(db.scalars(query.order_by(AISuggestion.id)))


def get_suggestion(db: Session, suggestion_id: int) -> AISuggestion:
    suggestion = db.get(AISuggestion, suggestion_id)
    if suggestion is None:
        raise NotFoundError("Cette suggestion n'existe pas.")
    return suggestion


def _require_pending(suggestion: AISuggestion) -> None:
    if suggestion.status != "pending":
        raise AppError("suggestion_not_pending", "Cette suggestion a déjà été traitée.", 409)


def find_occurrences(content: str, text: str) -> list[int]:
    positions: list[int] = []
    start = content.find(text)
    while start != -1:
        positions.append(start)
        start = content.find(text, start + len(text))
    return positions


def accept_suggestion(db: Session, suggestion_id: int, occurrence: int | None) -> AcceptResult:
    """Applique une suggestion au cours courant, sans jamais deviner (SPEC §18.1)."""
    suggestion = get_suggestion(db, suggestion_id)
    _require_pending(suggestion)
    current = require_current_course(db, suggestion.chapter_id)
    content = current.content_markdown

    if suggestion.type == "warning":
        _decide(suggestion, "accepted")
        db.commit()
        return AcceptResult(suggestion, current)

    if not suggestion.original_text:
        new_content = f"{content.rstrip()}\n\n{suggestion.suggested_text.strip()}\n"
    else:
        positions = find_occurrences(content, suggestion.original_text)
        if not positions:
            suggestion.status = "outdated"
            db.commit()
            raise AppError(
                "suggestion_outdated",
                "Le passage visé n'existe plus dans le cours. Tu peux recopier la suggestion "
                "à la main.",
                409,
            )
        if len(positions) > 1 and occurrence is None:
            raise AppError(
                "suggestion_ambiguous",
                "Ce passage apparaît plusieurs fois dans le cours. Choisis lequel modifier.",
                409,
                details={"occurrences": _contexts(content, suggestion.original_text, positions)},
            )
        index = occurrence or 0
        if not 0 <= index < len(positions):
            raise AppError("invalid_occurrence", "Ce passage n'existe pas.", 422)
        new_content = _apply(content, suggestion, positions[index])

    _decide(suggestion, "accepted")
    course = create_version(
        db,
        suggestion.chapter_id,
        new_content,
        origin="suggestion_applied",
        source_notes_hash=current.source_notes_hash,
    )
    db.commit()
    return AcceptResult(suggestion, course)


def reject_suggestion(db: Session, suggestion_id: int) -> AISuggestion:
    suggestion = get_suggestion(db, suggestion_id)
    _require_pending(suggestion)
    _decide(suggestion, "rejected")
    db.commit()
    return suggestion


def _decide(suggestion: AISuggestion, status: str) -> None:
    suggestion.status = status
    suggestion.decided_at = utcnow()


def _apply(content: str, suggestion: AISuggestion, position: int) -> str:
    end = position + len(suggestion.original_text)
    if suggestion.type in REPLACING_TYPES:
        return content[:position] + suggestion.suggested_text + content[end:]
    # addition : après le bloc qui contient le passage, sans casser tableau ni liste.
    return insert_addition(content, end, suggestion.suggested_text)


def _contexts(content: str, text: str, positions: list[int]) -> list[dict[str, str | int]]:
    return [
        {
            "index": index,
            "before": content[max(0, pos - CONTEXT_CHARS) : pos],
            "match": text,
            "after": content[pos + len(text) : pos + len(text) + CONTEXT_CHARS],
        }
        for index, pos in enumerate(positions)
    ]
