from fastapi import APIRouter

from app.api.chapters import chapters_out
from app.api.deps import DbDep, SettingsDep, StudentDep
from app.schemas.api import ChapterOut, SubjectOut, TrashItemOut
from app.services import trash_service

router = APIRouter(prefix="/api/trash", tags=["trash"])


@router.get("")
def list_trash(db: DbDep, student: StudentDep) -> list[TrashItemOut]:
    return [
        TrashItemOut(
            id=c.id,
            title=c.title,
            subject=SubjectOut.model_validate(c.subject),
            deleted_at=c.deleted_at,
            expires_at=trash_service.expires_at(c.deleted_at),
        )
        for c in trash_service.list_trash(db, student.id)
        if c.deleted_at is not None
    ]


@router.post("/{chapter_id}/restore")
def restore(chapter_id: int, db: DbDep) -> ChapterOut:
    return chapters_out(db, [trash_service.restore(db, chapter_id)])[0]


@router.delete("/{chapter_id}", status_code=204)
def purge(chapter_id: int, db: DbDep, settings: SettingsDep) -> None:
    trash_service.purge(db, settings, chapter_id)
