from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.errors import AppError, NotFoundError
from app.levels import ADAPTATION_IDS, DEFAULT_LEVEL, LEVEL_IDS
from app.models import Chapter, Student
from app.schemas.api import StudentCreate, StudentUpdate
from app.services import subject_service


def seed_default_student(db: Session) -> None:
    """Crée le premier élève au premier démarrage. Idempotent."""
    if db.scalar(select(func.count()).select_from(Student)) == 0:
        student = Student(name="Élève", level=DEFAULT_LEVEL)
        db.add(student)
        db.flush()
        subject_service.apply_level_defaults(db, student)
        db.commit()


def list_students(db: Session) -> list[Student]:
    return list(db.scalars(select(Student).order_by(Student.id)))


def get_student(db: Session, student_id: int) -> Student:
    student = db.get(Student, student_id)
    if student is None:
        raise NotFoundError("Cet élève n'existe pas.")
    return student


def resolve_student(db: Session, student_id: int | None) -> Student:
    """L'élève demandé, ou le premier si le navigateur n'en a pas encore choisi (ou plus)."""
    if student_id is not None:
        student = db.get(Student, student_id)
        if student is not None:
            return student
    student = db.scalars(select(Student).order_by(Student.id).limit(1)).first()
    if student is None:
        raise AppError("no_student", "Aucun élève n'est enregistré.", 409)
    return student


def _check_level(level: str) -> None:
    if level not in LEVEL_IDS:
        raise AppError("unknown_level", "Cette classe n'existe pas.", 422)


def _codes(codes: list[str]) -> str:
    unknown = [c for c in codes if c not in ADAPTATION_IDS]
    if unknown:
        raise AppError("unknown_adaptation", "Cette particularité n'existe pas.", 422)
    return ",".join(dict.fromkeys(codes))  # sans doublon, ordre conservé


def create_student(db: Session, data: StudentCreate) -> Student:
    _check_level(data.level)
    student = Student(
        name=data.name.strip(),
        level=data.level,
        adaptation_codes=_codes(data.adaptation_codes),
        adaptation_notes=data.adaptation_notes.strip(),
    )
    db.add(student)
    db.flush()
    subject_service.apply_level_defaults(db, student)
    db.commit()
    return student


def update_student(db: Session, student_id: int, data: StudentUpdate) -> Student:
    student = get_student(db, student_id)
    if data.name is not None:
        student.name = data.name.strip()
    if data.level is not None:
        _check_level(data.level)
        changed = data.level != student.level
        student.level = data.level
        # Tant qu'il n'a aucun chapitre, ses matières suivent sa classe.
        if changed and not db.scalar(select(func.count()).where(Chapter.student_id == student_id)):
            subject_service.apply_level_defaults(db, student)
    if data.adaptation_codes is not None:
        student.adaptation_codes = _codes(data.adaptation_codes)
    if data.adaptation_notes is not None:
        student.adaptation_notes = data.adaptation_notes.strip()
    db.commit()
    return student


def delete_student(db: Session, student_id: int) -> None:
    """Un élève n'est supprimé que s'il n'a aucun chapitre (corbeille comprise)."""
    student = get_student(db, student_id)
    if len(list_students(db)) <= 1:
        raise AppError("last_student", "Il faut garder au moins un élève.", 409)
    chapters = db.scalar(select(func.count()).where(Chapter.student_id == student_id))
    if chapters:
        raise AppError(
            "student_has_chapters",
            "Cet élève a encore des chapitres (corbeille comprise) : supprimez-les d'abord.",
            409,
        )
    subject_service.forget_student(db, student_id)
    db.delete(student)
    db.commit()
