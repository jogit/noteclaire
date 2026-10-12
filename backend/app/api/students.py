from fastapi import APIRouter

from app.api.deps import DbDep
from app.levels import ADAPTATIONS, LEVELS
from app.models import Student
from app.schemas.api import (
    AdaptationOut,
    LevelOut,
    StudentCreate,
    StudentOut,
    StudentSubjectsIn,
    StudentUpdate,
)
from app.services import student_service, subject_service

router = APIRouter(prefix="/api", tags=["students"])


def _out(db: DbDep, student: Student) -> StudentOut:
    out = StudentOut.model_validate(student)
    out.subject_ids = sorted(subject_service.enabled_ids(db, student.id))
    return out


@router.get("/levels")
def get_levels() -> list[LevelOut]:
    return [LevelOut(id=level_id, name=name) for level_id, name, _ in LEVELS]


@router.get("/adaptations")
def get_adaptations() -> list[AdaptationOut]:
    return [AdaptationOut(id=adaptation_id, name=name) for adaptation_id, name, _ in ADAPTATIONS]


@router.get("/students")
def get_students(db: DbDep) -> list[StudentOut]:
    return [_out(db, s) for s in student_service.list_students(db)]


@router.post("/students", status_code=201)
def create_student(data: StudentCreate, db: DbDep) -> StudentOut:
    return _out(db, student_service.create_student(db, data))


@router.patch("/students/{student_id}")
def update_student(student_id: int, data: StudentUpdate, db: DbDep) -> StudentOut:
    return _out(db, student_service.update_student(db, student_id, data))


@router.put("/students/{student_id}/subjects")
def set_subjects(student_id: int, data: StudentSubjectsIn, db: DbDep) -> StudentOut:
    student = student_service.get_student(db, student_id)
    subject_service.set_student_subjects(db, student_id, data.subject_ids)
    return _out(db, student)


@router.delete("/students/{student_id}", status_code=204)
def delete_student(student_id: int, db: DbDep) -> None:
    student_service.delete_student(db, student_id)
