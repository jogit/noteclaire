from fastapi import APIRouter

from app.api.deps import DbDep, StudentDep
from app.models import Subject
from app.schemas.api import SubjectCreate, SubjectOut, SubjectUpdate
from app.services import subject_service
from app.subjects import DEFAULTS_BY_LEVEL

router = APIRouter(prefix="/api/subjects", tags=["subjects"])


def _out(subject: Subject, *, enabled: bool = True, count: int = 0) -> SubjectOut:
    return SubjectOut(
        id=subject.id,
        name=subject.name,
        slug=subject.slug,
        enabled=enabled,
        usual_for=[level for level, slugs in DEFAULTS_BY_LEVEL.items() if subject.slug in slugs],
        chapter_count=count,
    )


@router.get("")
def get_subjects(db: DbDep, student: StudentDep, include_all: bool = False) -> list[SubjectOut]:
    """Matières de l'élève courant ; `include_all` : tout le catalogue, avec `enabled`."""
    counts = subject_service.chapter_counts(db, student.id)
    enabled = subject_service.enabled_ids(db, student.id)
    subjects = subject_service.list_subjects(db, student.id, include_all=include_all)
    return [_out(s, enabled=s.id in enabled, count=counts.get(s.id, 0)) for s in subjects]


@router.post("", status_code=201)
def create_subject(data: SubjectCreate, db: DbDep, student: StudentDep) -> SubjectOut:
    return _out(subject_service.create_subject(db, student.id, data))


@router.patch("/{subject_id}")
def update_subject(
    subject_id: int, data: SubjectUpdate, db: DbDep, student: StudentDep
) -> SubjectOut:
    subject = subject_service.update_subject(db, subject_id, data)
    return _out(subject, enabled=subject.id in subject_service.enabled_ids(db, student.id))


@router.delete("/{subject_id}", status_code=204)
def delete_subject(subject_id: int, db: DbDep) -> None:
    subject_service.delete_subject(db, subject_id)
