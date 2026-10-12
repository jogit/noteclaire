from dataclasses import asdict

from fastapi import APIRouter

from app.api.deps import AIProviderDep, DbDep, SettingsDep, StudentDep
from app.models import Chapter, Course, NoteVersion
from app.schemas.api import (
    ChapterCreate,
    ChapterOut,
    ChapterProgressOut,
    ChapterUpdate,
    CourseIn,
    CourseOut,
    CourseVersionContentOut,
    CourseVersionOut,
    NotesIn,
    NotesOut,
    NoteVersionContentOut,
    NoteVersionOut,
    SuggestionOut,
)
from app.services import chapter_service, course_service, suggestion_service

router = APIRouter(prefix="/api/chapters", tags=["chapters"])


def chapters_out(db: DbDep, chapters: list[Chapter]) -> list[ChapterOut]:
    progress = chapter_service.chapters_progress(db, chapters)
    return [
        ChapterOut.model_validate(c).model_copy(
            update={"progress": ChapterProgressOut(**asdict(progress[c.id]))}
        )
        for c in chapters
    ]


@router.get("")
def list_chapters(
    db: DbDep, student: StudentDep, subject_id: int | None = None
) -> list[ChapterOut]:
    return chapters_out(db, chapter_service.list_chapters(db, student.id, subject_id))


@router.post("", status_code=201)
def create_chapter(data: ChapterCreate, db: DbDep, student: StudentDep) -> ChapterOut:
    return chapters_out(db, [chapter_service.create_chapter(db, student.id, data)])[0]


@router.get("/{chapter_id}")
def get_chapter(chapter_id: int, db: DbDep) -> ChapterOut:
    return chapters_out(db, [chapter_service.get_chapter(db, chapter_id)])[0]


@router.patch("/{chapter_id}")
def update_chapter(chapter_id: int, data: ChapterUpdate, db: DbDep) -> ChapterOut:
    return chapters_out(db, [chapter_service.update_chapter(db, chapter_id, data)])[0]


@router.delete("/{chapter_id}", status_code=204)
def delete_chapter(chapter_id: int, db: DbDep) -> None:
    """Met le chapitre à la corbeille (images gardées jusqu'à la suppression définitive)."""
    chapter_service.delete_chapter(db, chapter_id)


@router.get("/{chapter_id}/notes")
def get_notes(chapter_id: int, db: DbDep) -> NotesOut:
    return NotesOut.model_validate(chapter_service.get_chapter(db, chapter_id).note)


@router.put("/{chapter_id}/notes")
def put_notes(chapter_id: int, data: NotesIn, db: DbDep) -> NotesOut:
    note = chapter_service.save_notes(
        db, chapter_id, data.raw_text, data.source, checkpoint=data.checkpoint
    )
    return NotesOut.model_validate(note)


def version_out(version: NoteVersion) -> NoteVersionOut:
    text = " ".join(version.raw_text.split())
    return NoteVersionOut(
        id=version.id,
        reason=version.reason,
        source=version.source,
        created_at=version.created_at,
        words=len(version.raw_text.split()),
        preview=text[:140] + ("…" if len(text) > 140 else ""),
    )


@router.get("/{chapter_id}/notes/versions")
def list_note_versions(chapter_id: int, db: DbDep) -> list[NoteVersionOut]:
    return [version_out(v) for v in chapter_service.list_note_versions(db, chapter_id)]


@router.get("/{chapter_id}/notes/versions/{version_id}")
def get_note_version(chapter_id: int, version_id: int, db: DbDep) -> NoteVersionContentOut:
    version = chapter_service.get_note_version(db, chapter_id, version_id)
    return NoteVersionContentOut(**version_out(version).model_dump(), raw_text=version.raw_text)


@router.post("/{chapter_id}/notes/versions/{version_id}/restore")
def restore_note_version(chapter_id: int, version_id: int, db: DbDep) -> NotesOut:
    note = chapter_service.restore_note_version(db, chapter_id, version_id)
    return NotesOut.model_validate(note)


@router.get("/{chapter_id}/course")
def get_course(chapter_id: int, db: DbDep) -> CourseOut:
    return course_out(db, course_service.require_current_course(db, chapter_id))


@router.put("/{chapter_id}/course")
def put_course(chapter_id: int, data: CourseIn, db: DbDep) -> CourseOut:
    return course_out(db, course_service.edit_course(db, chapter_id, data.content_markdown))


@router.get("/{chapter_id}/course/versions")
def list_versions(chapter_id: int, db: DbDep) -> list[CourseVersionOut]:
    versions = course_service.list_versions(db, chapter_id)
    return [CourseVersionOut.model_validate(v) for v in versions]


@router.get("/{chapter_id}/course/versions/{version}")
def get_version(chapter_id: int, version: int, db: DbDep) -> CourseVersionContentOut:
    course = course_service.get_version(db, chapter_id, version)
    return CourseVersionContentOut.model_validate(course)


@router.post("/{chapter_id}/structure", status_code=201)
async def structure(
    chapter_id: int, db: DbDep, settings: SettingsDep, provider: AIProviderDep
) -> CourseOut:
    course = await course_service.structure_chapter(db, settings, chapter_id, provider)
    return course_out(db, course)


@router.post("/{chapter_id}/analyze", status_code=201)
async def analyze(
    chapter_id: int, db: DbDep, settings: SettingsDep, provider: AIProviderDep
) -> list[SuggestionOut]:
    suggestions = await suggestion_service.analyze_chapter(db, settings, chapter_id, provider)
    return [SuggestionOut.model_validate(s) for s in suggestions]


@router.get("/{chapter_id}/suggestions")
def list_suggestions(chapter_id: int, db: DbDep, status: str | None = None) -> list[SuggestionOut]:
    suggestions = suggestion_service.list_suggestions(db, chapter_id, status)
    return [SuggestionOut.model_validate(s) for s in suggestions]


def course_out(db: DbDep, course: Course) -> CourseOut:
    raw_text = chapter_service.get_chapter(db, course.chapter_id).note.raw_text
    return CourseOut(
        chapter_id=course.chapter_id,
        content_markdown=course.content_markdown,
        version=course.version,
        origin=course.origin,
        created_at=course.created_at,
        notes_changed=course_service.notes_changed_since(course, raw_text),
        has_manual_changes=course_service.has_manual_changes(course),
        title=course_service.course_title(course.content_markdown),
    )
