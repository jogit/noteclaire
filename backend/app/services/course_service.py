import hashlib
import logging
import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.errors import AppError, NotFoundError
from app.levels import adaptations_text, prompt_label
from app.models import AISuggestion, Course
from app.prompts import prompt_version
from app.services.ai.base import AIProvider, AIProviderError, StructureRequest, StructureResponse
from app.services.ai_runs import run_ai
from app.services.chapter_service import add_note_version, get_chapter
from app.services.fidelity import keeps_notes
from app.services.search_service import index_chapter

logger = logging.getLogger(__name__)


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def get_current_course(db: Session, chapter_id: int) -> Course | None:
    return db.scalars(
        select(Course).where(Course.chapter_id == chapter_id).order_by(Course.version.desc())
    ).first()


def require_current_course(db: Session, chapter_id: int) -> Course:
    get_chapter(db, chapter_id)
    course = get_current_course(db, chapter_id)
    if course is None:
        raise NotFoundError("Ce chapitre n'a pas encore été mis au propre.")
    return course


def course_title(content: str) -> str:
    """Titre du cours : son premier titre de niveau 1, s'il y en a un."""
    for line in content.splitlines():
        match = re.match(r"^#\s+(.+?)\s*#*\s*$", line)
        if match:
            return match.group(1).strip()
    return ""


def notes_changed_since(course: Course, raw_text: str) -> bool:
    return sha256(raw_text) != course.source_notes_hash


def has_manual_changes(course: Course) -> bool:
    """Vrai si le cours courant a été modifié depuis la dernière mise au propre (SPEC §9.1).

    Les versions sont linéaires : toute modification après la dernière mise au propre
    est forcément la version courante.
    """
    return course.origin != "ai_structure"


def create_version(
    db: Session,
    chapter_id: int,
    content: str,
    origin: str,
    source_notes_hash: str,
    ai_run_id: int | None = None,
) -> Course:
    """Ajoute une version du cours. Les versions existantes ne sont jamais modifiées."""
    current = db.scalar(select(func.max(Course.version)).where(Course.chapter_id == chapter_id))
    course = Course(
        chapter_id=chapter_id,
        content_markdown=content,
        version=(current or 0) + 1,
        origin=origin,
        source_notes_hash=source_notes_hash,
        ai_run_id=ai_run_id,
    )
    db.add(course)
    db.flush()
    _mark_outdated_suggestions(db, chapter_id, content)
    index_chapter(db, chapter_id)
    return course


def _mark_outdated_suggestions(db: Session, chapter_id: int, content: str) -> None:
    pending = db.scalars(
        select(AISuggestion).where(
            AISuggestion.chapter_id == chapter_id, AISuggestion.status == "pending"
        )
    )
    for suggestion in pending:
        if suggestion.original_text and suggestion.original_text not in content:
            suggestion.status = "outdated"


async def structure_chapter(
    db: Session, settings: Settings, chapter_id: int, provider: AIProvider
) -> Course:
    """Met au propre les notes et crée une nouvelle version du cours. Les notes ne changent pas."""
    chapter = get_chapter(db, chapter_id)
    raw_text = chapter.note.raw_text
    if not raw_text.strip():
        raise AppError("empty_notes", "Tes notes sont vides : il n'y a rien à mettre au propre.")
    # Garde les notes telles qu'elles étaient au moment de la mise au propre.
    add_note_version(db, chapter_id, raw_text, chapter.note.source, "structure")
    db.commit()

    request = StructureRequest(
        subject=chapter.subject.name,
        chapter=chapter.title,
        raw_notes=raw_text,
        level=prompt_label(chapter.student.level),
        adaptations=adaptations_text(
            chapter.student.adaptation_codes, chapter.student.adaptation_notes
        ),
    )

    async def structure_faithfully() -> StructureResponse:
        response = await provider.structure_course(request)
        if not keeps_notes(raw_text, response.result.clean_course):
            # Cours résumé, réécrit ou complété : même traitement qu'une réponse inutilisable.
            logger.info("structure chapter=%s unfaithful", chapter_id)
            raise AIProviderError("ai_invalid_response")
        return response

    response, run = await run_ai(
        db,
        settings,
        structure_faithfully,
        chapter_id=chapter_id,
        operation="structure",
        provider=provider.name,
        model=provider.model,
        prompt_version=prompt_version("structure"),
        enforce_budget=provider.paid,
        input_hash=sha256(
            "\n".join(
                [
                    prompt_version("structure"),
                    request.subject,
                    request.level,
                    request.chapter,
                    request.adaptations,
                    raw_text,
                ]
            )
        ),
    )
    course = create_version(
        db,
        chapter_id,
        response.result.clean_course,
        origin="ai_structure",
        source_notes_hash=sha256(raw_text),
        ai_run_id=run.id,
    )
    db.commit()
    return course


def edit_course(db: Session, chapter_id: int, content: str) -> Course:
    """Modification manuelle : crée une version `user_edit` (sauf si rien n'a changé)."""
    current = require_current_course(db, chapter_id)
    if not content.strip():
        raise AppError("empty_course", "Le cours ne peut pas être vide.")
    if content == current.content_markdown:
        return current
    course = create_version(
        db, chapter_id, content, origin="user_edit", source_notes_hash=current.source_notes_hash
    )
    db.commit()
    return course


def list_versions(db: Session, chapter_id: int) -> list[Course]:
    get_chapter(db, chapter_id)
    return list(
        db.scalars(
            select(Course).where(Course.chapter_id == chapter_id).order_by(Course.version.desc())
        )
    )


def get_version(db: Session, chapter_id: int, version: int) -> Course:
    course = db.scalar(
        select(Course).where(Course.chapter_id == chapter_id, Course.version == version)
    )
    if course is None:
        raise NotFoundError("Cette version n'existe pas.")
    return course
