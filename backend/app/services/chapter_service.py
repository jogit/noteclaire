import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.errors import AppError, NotFoundError
from app.models import (
    AISuggestion,
    Chapter,
    Course,
    Note,
    NoteVersion,
    Quiz,
    RevisionSheet,
    Subject,
)
from app.models.entities import utcnow
from app.schemas.api import ChapterCreate, ChapterUpdate
from app.services.search_service import index_chapter

# Historique des notes : une version automatique au plus toutes les 15 minutes de saisie.
AUTO_VERSION_INTERVAL = timedelta(minutes=15)
MAX_NOTE_VERSIONS = 50


def get_chapter(db: Session, chapter_id: int, *, include_deleted: bool = False) -> Chapter:
    """Chapitre actif. Un chapitre dans la corbeille est introuvable, sauf pour la corbeille."""
    chapter = db.get(Chapter, chapter_id)
    if chapter is None or (chapter.deleted_at is not None and not include_deleted):
        raise NotFoundError("Ce chapitre n'existe pas.")
    return chapter


def list_chapters(db: Session, student_id: int, subject_id: int | None) -> list[Chapter]:
    query = (
        select(Chapter)
        .where(Chapter.deleted_at.is_(None), Chapter.student_id == student_id)
        .order_by(Chapter.updated_at.desc())
    )
    if subject_id is not None:
        query = query.where(Chapter.subject_id == subject_id)
    return list(db.scalars(query))


def create_chapter(db: Session, student_id: int, data: ChapterCreate) -> Chapter:
    if db.get(Subject, data.subject_id) is None:
        raise AppError("unknown_subject", "Cette matière n'existe pas.", 422)
    chapter = Chapter(
        student_id=student_id,
        subject_id=data.subject_id,
        title=data.title.strip(),
        description=data.description,
        school_year=data.school_year,
    )
    chapter.note = Note(raw_text="", source="keyboard")
    db.add(chapter)
    db.flush()
    index_chapter(db, chapter.id)
    db.commit()
    return chapter


def update_chapter(db: Session, chapter_id: int, data: ChapterUpdate) -> Chapter:
    chapter = get_chapter(db, chapter_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(chapter, field, value.strip() if field == "title" else value)
    index_chapter(db, chapter_id)
    db.commit()
    return chapter


def delete_chapter(db: Session, chapter_id: int) -> None:
    """Met le chapitre à la corbeille : il reste récupérable pendant 30 jours."""
    chapter = get_chapter(db, chapter_id)
    chapter.deleted_at = utcnow()
    db.flush()
    index_chapter(db, chapter_id)  # retire le chapitre de la recherche
    db.commit()


def save_notes(
    db: Session,
    chapter_id: int,
    raw_text: str,
    source: str | None,
    checkpoint: str | None = None,
) -> Note:
    """Enregistre les notes et garde des versions pour pouvoir revenir en arrière.

    - avant une modification, l'état précédent est gardé s'il date de plus de 15 minutes
      ou si la modification efface une grande partie du texte ;
    - checkpoint="photo" garde aussi le texte tout juste importé d'une photo.
    """
    chapter = get_chapter(db, chapter_id)
    note = chapter.note
    changed = note.raw_text != raw_text or (source is not None and note.source != source)
    if changed:
        previous = note.raw_text
        if previous.strip() and previous != raw_text:
            if _is_big_deletion(previous, raw_text):
                add_note_version(db, chapter_id, previous, note.source, "big_deletion")
            elif _auto_version_due(db, chapter_id):
                add_note_version(db, chapter_id, previous, note.source, "auto")
        note.raw_text = raw_text
        if source is not None:
            note.source = source
        chapter.updated_at = utcnow()
        index_chapter(db, chapter_id)
    if checkpoint is not None:
        add_note_version(db, chapter_id, raw_text, note.source, checkpoint)
    db.commit()
    return note


def _is_big_deletion(previous: str, new: str) -> bool:
    before, after = len(previous.split()), len(new.split())
    return before >= 20 and after < before * 0.6


def _latest_version(db: Session, chapter_id: int) -> NoteVersion | None:
    return db.scalar(
        select(NoteVersion)
        .where(NoteVersion.chapter_id == chapter_id)
        .order_by(NoteVersion.id.desc())
        .limit(1)
    )


def _auto_version_due(db: Session, chapter_id: int) -> bool:
    latest = _latest_version(db, chapter_id)
    return latest is None or utcnow() - as_utc(latest.created_at) >= AUTO_VERSION_INTERVAL


def as_utc(value: datetime) -> datetime:
    """SQLite rend des dates sans fuseau : elles sont toujours en UTC."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def add_note_version(
    db: Session, chapter_id: int, raw_text: str, source: str, reason: str
) -> NoteVersion | None:
    """Ajoute une version (sauf texte vide ou identique à la dernière) et garde les 50 dernières.

    Ne valide pas la transaction : c'est à l'appelant de le faire.
    """
    if not raw_text.strip():
        return None
    latest = _latest_version(db, chapter_id)
    if latest is not None and latest.raw_text == raw_text:
        return None
    version = NoteVersion(chapter_id=chapter_id, raw_text=raw_text, source=source, reason=reason)
    db.add(version)
    db.flush()
    keep = select(NoteVersion.id).where(NoteVersion.chapter_id == chapter_id)
    keep = keep.order_by(NoteVersion.id.desc())
    db.execute(
        delete(NoteVersion).where(
            NoteVersion.chapter_id == chapter_id,
            NoteVersion.id.not_in(keep.limit(MAX_NOTE_VERSIONS).scalar_subquery()),
        )
    )
    return version


def list_note_versions(db: Session, chapter_id: int) -> list[NoteVersion]:
    get_chapter(db, chapter_id)
    return list(
        db.scalars(
            select(NoteVersion)
            .where(NoteVersion.chapter_id == chapter_id)
            .order_by(NoteVersion.id.desc())
        )
    )


def get_note_version(db: Session, chapter_id: int, version_id: int) -> NoteVersion:
    get_chapter(db, chapter_id)
    version = db.get(NoteVersion, version_id)
    if version is None or version.chapter_id != chapter_id:
        raise NotFoundError("Cette version des notes n'existe pas.")
    return version


def restore_note_version(db: Session, chapter_id: int, version_id: int) -> Note:
    """Remet une ancienne version. Les notes actuelles sont gardées dans l'historique."""
    version = get_note_version(db, chapter_id, version_id)
    note = get_chapter(db, chapter_id).note
    add_note_version(db, chapter_id, note.raw_text, note.source, "before_restore")
    raw_text, source = version.raw_text, version.source
    return save_notes(db, chapter_id, raw_text, source)


@dataclass(frozen=True)
class ChapterProgress:
    """Avancement d'un chapitre, pour l'accueil et la liste des chapitres."""

    notes_words: int
    course_version: int | None
    notes_changed: bool
    pending_suggestions: int
    has_revision_sheet: bool
    has_quiz: bool


def chapters_progress(db: Session, chapters: list[Chapter]) -> dict[int, ChapterProgress]:
    """Avancement de plusieurs chapitres en quelques requêtes groupées."""
    ids = [c.id for c in chapters]
    if not ids:
        return {}
    latest = (
        select(Course.chapter_id, func.max(Course.version).label("version"))
        .where(Course.chapter_id.in_(ids))
        .group_by(Course.chapter_id)
        .subquery()
    )
    courses = {
        chapter_id: (version, notes_hash)
        for chapter_id, version, notes_hash in db.execute(
            select(Course.chapter_id, Course.version, Course.source_notes_hash).join(
                latest,
                (Course.chapter_id == latest.c.chapter_id) & (Course.version == latest.c.version),
            )
        )
    }
    pending = dict(
        db.execute(
            select(AISuggestion.chapter_id, func.count())
            .where(AISuggestion.chapter_id.in_(ids), AISuggestion.status == "pending")
            .group_by(AISuggestion.chapter_id)
        ).all()
    )
    sheets = set(
        db.scalars(select(RevisionSheet.chapter_id).where(RevisionSheet.chapter_id.in_(ids)))
    )
    quizzes = set(db.scalars(select(Quiz.chapter_id).where(Quiz.chapter_id.in_(ids))))

    progress: dict[int, ChapterProgress] = {}
    for chapter in chapters:
        raw = chapter.note.raw_text if chapter.note else ""
        course = courses.get(chapter.id)
        progress[chapter.id] = ChapterProgress(
            notes_words=len(raw.split()),
            course_version=course[0] if course else None,
            notes_changed=course is not None
            and hashlib.sha256(raw.encode("utf-8")).hexdigest() != course[1],
            pending_suggestions=int(pending.get(chapter.id, 0)),
            has_revision_sheet=chapter.id in sheets,
            has_quiz=chapter.id in quizzes,
        )
    return progress
