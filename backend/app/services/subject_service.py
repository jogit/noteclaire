import re
import unicodedata

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.errors import AppError, NotFoundError
from app.models import Chapter, ReferenceDocument, Student, StudentSubject, Subject
from app.schemas.api import SubjectCreate, SubjectUpdate
from app.subjects import DEFAULTS_BY_LEVEL, SUBJECTS


def seed_subjects(db: Session) -> None:
    """Crée les matières de départ si la table est vide (une matière supprimée ne revient pas)."""
    if db.scalar(select(func.count()).select_from(Subject)):
        return
    for position, (slug, name) in enumerate(SUBJECTS):
        db.add(Subject(slug=slug, name=name, position=position))
    db.commit()


def enabled_ids(db: Session, student_id: int) -> set[int]:
    return set(
        db.scalars(select(StudentSubject.subject_id).where(StudentSubject.student_id == student_id))
    )


def list_subjects(db: Session, student_id: int, *, include_all: bool = False) -> list[Subject]:
    """Matières de l'élève (ou tout le catalogue commun avec `include_all`), dans l'ordre."""
    subjects = list(db.scalars(select(Subject).order_by(Subject.position, Subject.id)))
    if include_all:
        return subjects
    enabled = enabled_ids(db, student_id)
    return [s for s in subjects if s.id in enabled]


def set_enabled(db: Session, student_id: int, subject_id: int, enabled: bool) -> None:
    link = db.get(StudentSubject, (student_id, subject_id))
    if enabled and link is None:
        db.add(StudentSubject(student_id=student_id, subject_id=subject_id))
    elif not enabled and link is not None:
        db.delete(link)


def set_student_subjects(db: Session, student_id: int, subject_ids: list[int]) -> None:
    """Remplace les matières suivies par l'élève (les matières inconnues sont refusées)."""
    known = set(db.scalars(select(Subject.id)))
    if any(subject_id not in known for subject_id in subject_ids):
        raise AppError("unknown_subject", "Cette matière n'existe pas.", 422)
    wanted = set(subject_ids)
    for subject_id in known:
        set_enabled(db, student_id, subject_id, subject_id in wanted)
    db.commit()


def apply_level_defaults(db: Session, student: Student) -> None:
    """Active les matières habituelles de la classe de l'élève (remplace sa sélection)."""
    defaults = DEFAULTS_BY_LEVEL.get(student.level, set())
    db.execute(delete(StudentSubject).where(StudentSubject.student_id == student.id))
    for subject in db.scalars(select(Subject)):
        if subject.slug in defaults:
            db.add(StudentSubject(student_id=student.id, subject_id=subject.id))


def forget_student(db: Session, student_id: int) -> None:
    db.execute(delete(StudentSubject).where(StudentSubject.student_id == student_id))


def get_subject(db: Session, subject_id: int) -> Subject:
    subject = db.get(Subject, subject_id)
    if subject is None:
        raise NotFoundError("Cette matière n'existe pas.")
    return subject


def _slugify(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-") or "matiere"


def _check_name_free(db: Session, name: str, *, except_id: int | None = None) -> None:
    taken = db.scalars(select(Subject).where(func.lower(Subject.name) == name.lower()))
    if any(s.id != except_id for s in taken):
        raise AppError("subject_exists", "Cette matière existe déjà.", 409)


def create_subject(db: Session, student_id: int, data: SubjectCreate) -> Subject:
    """Activée pour l'élève courant. Le slug (dossier des références) vient du nom, sans changer."""
    name = data.name.strip()
    _check_name_free(db, name)
    base = _slugify(name)
    existing = set(db.scalars(select(Subject.slug)))
    slug, counter = base, 2
    while slug in existing:
        slug = f"{base}-{counter}"
        counter += 1
    last = db.scalar(select(func.max(Subject.position))) or 0
    subject = Subject(name=name, slug=slug, position=last + 1)
    db.add(subject)
    db.flush()
    set_enabled(db, student_id, subject.id, True)
    db.commit()
    return subject


def update_subject(db: Session, subject_id: int, data: SubjectUpdate) -> Subject:
    subject = get_subject(db, subject_id)
    if data.name is not None:
        name = data.name.strip()
        _check_name_free(db, name, except_id=subject_id)
        subject.name = name
    db.commit()
    return subject


def delete_subject(db: Session, subject_id: int) -> None:
    """Seule une matière sans chapitre (corbeille comprise) ni document peut être supprimée."""
    subject = get_subject(db, subject_id)
    chapters = db.scalar(select(func.count()).where(Chapter.subject_id == subject_id))
    documents = db.scalar(select(func.count()).where(ReferenceDocument.subject_id == subject_id))
    if chapters or documents:
        raise AppError(
            "subject_not_empty",
            "Cette matière a encore des chapitres ou des documents de référence : "
            "désactivez-la plutôt que de la supprimer.",
            409,
        )
    db.execute(delete(StudentSubject).where(StudentSubject.subject_id == subject_id))
    db.delete(subject)
    db.commit()


def chapter_counts(db: Session, student_id: int) -> dict[int, int]:
    rows = db.execute(
        select(Chapter.subject_id, func.count())
        .where(Chapter.deleted_at.is_(None), Chapter.student_id == student_id)
        .group_by(Chapter.subject_id)
    )
    return {subject_id: int(count) for subject_id, count in rows}
