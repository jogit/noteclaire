"""Corbeille : les chapitres supprimés restent récupérables pendant 30 jours."""

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.errors import NotFoundError
from app.models import Chapter
from app.models.entities import utcnow
from app.services import image_service, photo_service
from app.services.chapter_service import as_utc, get_chapter
from app.services.search_service import index_chapter

TRASH_RETENTION = timedelta(days=30)


def list_trash(db: Session, student_id: int | None = None) -> list[Chapter]:
    """Chapitres à la corbeille d'un élève (ou de tous, pour le nettoyage automatique)."""
    query = select(Chapter).where(Chapter.deleted_at.is_not(None))
    if student_id is not None:
        query = query.where(Chapter.student_id == student_id)
    return list(db.scalars(query.order_by(Chapter.deleted_at.desc())))


def expires_at(deleted_at: datetime) -> datetime:
    return as_utc(deleted_at) + TRASH_RETENTION


def _trashed(db: Session, chapter_id: int) -> Chapter:
    chapter = get_chapter(db, chapter_id, include_deleted=True)
    if chapter.deleted_at is None:
        raise NotFoundError("Ce chapitre n'est pas dans la corbeille.")
    return chapter


def restore(db: Session, chapter_id: int) -> Chapter:
    chapter = _trashed(db, chapter_id)
    chapter.deleted_at = None
    chapter.updated_at = utcnow()
    db.flush()
    index_chapter(db, chapter_id)
    db.commit()
    return chapter


def purge(db: Session, settings: Settings, chapter_id: int) -> None:
    """Efface définitivement le chapitre, tout ce qui en dépend et ses images."""
    db.delete(_trashed(db, chapter_id))
    db.commit()
    image_service.delete_chapter_images(settings, chapter_id)
    photo_service.delete_chapter_photos(settings, chapter_id)


def purge_expired(db: Session, settings: Settings) -> int:
    """Efface les chapitres restés plus de 30 jours dans la corbeille."""
    now = utcnow()
    expired = [
        c.id for c in list_trash(db) if c.deleted_at is not None and expires_at(c.deleted_at) <= now
    ]
    for chapter_id in expired:
        purge(db, settings, chapter_id)
    return len(expired)
