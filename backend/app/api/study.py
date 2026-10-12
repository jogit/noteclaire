from datetime import UTC, datetime

from fastapi import APIRouter, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import AIProviderDep, DbDep, SettingsDep
from app.models import Course, Quiz, RevisionSheet
from app.schemas.api import (
    ExplainIn,
    ExplainOut,
    FigureOut,
    ImageOut,
    PhotoOut,
    QuizOut,
    QuizQuestionOut,
    RedrawIn,
    RedrawOut,
    RestyleIn,
    RevisionSheetOut,
    StoredPhotoOut,
    UncertainSpotOut,
)
from app.services import (
    chapter_service,
    course_service,
    export_service,
    figure_service,
    image_service,
    photo_service,
    study_service,
)

router = APIRouter(prefix="/api/chapters", tags=["study"])


def _version(db: Session, course_id: int) -> int:
    course = db.get(Course, course_id)
    return course.version if course else 0


def sheet_out(db: Session, sheet: RevisionSheet) -> RevisionSheetOut:
    return RevisionSheetOut(
        chapter_id=sheet.chapter_id,
        content_markdown=sheet.content_markdown,
        course_version=_version(db, sheet.course_version_id),
        outdated=study_service.is_outdated(db, sheet.chapter_id, sheet.course_version_id),
        created_at=sheet.created_at,
    )


def quiz_out(db: Session, quiz: Quiz) -> QuizOut:
    return QuizOut(
        chapter_id=quiz.chapter_id,
        questions=[QuizQuestionOut(**q.model_dump()) for q in study_service.quiz_questions(quiz)],
        course_version=_version(db, quiz.course_version_id),
        outdated=study_service.is_outdated(db, quiz.chapter_id, quiz.course_version_id),
        created_at=quiz.created_at,
    )


@router.post("/{chapter_id}/revision-sheet", status_code=201)
async def create_revision_sheet(
    chapter_id: int, db: DbDep, settings: SettingsDep, provider: AIProviderDep
) -> RevisionSheetOut:
    sheet = await study_service.generate_revision_sheet(db, settings, chapter_id, provider)
    return sheet_out(db, sheet)


@router.get("/{chapter_id}/revision-sheet")
def get_revision_sheet(chapter_id: int, db: DbDep) -> RevisionSheetOut:
    return sheet_out(db, study_service.latest_revision_sheet(db, chapter_id))


@router.post("/{chapter_id}/quiz", status_code=201)
async def create_quiz(
    chapter_id: int, db: DbDep, settings: SettingsDep, provider: AIProviderDep
) -> QuizOut:
    return quiz_out(db, await study_service.generate_quiz(db, settings, chapter_id, provider))


@router.get("/{chapter_id}/quiz")
def get_quiz(chapter_id: int, db: DbDep) -> QuizOut:
    return quiz_out(db, study_service.latest_quiz(db, chapter_id))


@router.get("/{chapter_id}/quiz/anki.txt")
def export_quiz_anki(chapter_id: int, db: DbDep) -> Response:
    """Le quiz du chapitre en cartes Anki (import texte, une carte par question)."""
    chapter = chapter_service.get_chapter(db, chapter_id)
    quiz = study_service.latest_quiz(db, chapter_id)
    content = export_service.anki_text(chapter, study_service.quiz_questions(quiz))
    filename = export_service.export_filename(chapter, "-anki.txt")
    return Response(
        content,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{chapter_id}/explain")
async def explain(
    chapter_id: int, data: ExplainIn, db: DbDep, settings: SettingsDep, provider: AIProviderDep
) -> ExplainOut:
    result = await study_service.explain_passage(
        db, settings, chapter_id, data.passage, data.mode, provider
    )
    return ExplainOut(text=result.text, answer=result.answer)


@router.post("/{chapter_id}/photo")
async def photo(
    chapter_id: int,
    image: UploadFile,
    db: DbDep,
    settings: SettingsDep,
    provider: AIProviderDep,
) -> PhotoOut:
    """Lit une photo de notes manuscrites ; la photo (sans métadonnées) est conservée."""
    data = await image.read(photo_service.MAX_PHOTO_BYTES + 1)
    result, url, jpeg = await photo_service.transcribe_photo(
        db, settings, chapter_id, data, image.content_type or "", provider
    )
    figures = await figure_service.crop_figures(
        db, settings, chapter_id, jpeg, result.text, provider
    )
    return PhotoOut(
        text=result.text,
        uncertain=[UncertainSpotOut(**spot.model_dump()) for spot in result.uncertain],
        url=url,
        figures=[FigureOut(index=f.position, url=f.url) for f in figures],
    )


@router.post("/{chapter_id}/schemas/redraw")
async def redraw_schema(
    chapter_id: int, data: RedrawIn, db: DbDep, settings: SettingsDep, provider: AIProviderDep
) -> RedrawOut:
    """Redessine proprement (SVG) un schéma du chapitre ; l'original n'est pas modifié."""
    redrawn = await figure_service.redraw_schema(
        db,
        settings,
        chapter_id,
        data.url,
        provider,
        data.previous_url,
        data.remark.strip(),
        data.hand,
    )
    return RedrawOut(url=redrawn.url, corrections=redrawn.corrections)


@router.post("/{chapter_id}/schemas/restyle")
def restyle_schema(chapter_id: int, data: RestyleIn, db: DbDep, settings: SettingsDep) -> RedrawOut:
    """Même schéma redessiné, avec ou sans aspect manuscrit (sans appel à l'IA)."""
    chapter_service.get_chapter(db, chapter_id)
    return RedrawOut(url=figure_service.restyle_schema(settings, chapter_id, data.url, data.hand))


@router.get("/{chapter_id}/photos")
def list_photos(chapter_id: int, db: DbDep, settings: SettingsDep) -> list[StoredPhotoOut]:
    """Les photos d'origine importées dans ce chapitre."""
    chapter_service.get_chapter(db, chapter_id)
    return [
        StoredPhotoOut(url=url, created_at=created)
        for url, created in photo_service.list_originals(settings, chapter_id)
    ]


@router.post("/{chapter_id}/images", status_code=201)
async def upload_image(
    chapter_id: int, image: UploadFile, db: DbDep, settings: SettingsDep
) -> ImageOut:
    """Ajoute une image au cours (ex. la photo d'un schéma)."""
    chapter_service.get_chapter(db, chapter_id)
    data = await image.read(photo_service.MAX_PHOTO_BYTES + 1)
    url = image_service.save_image(settings, chapter_id, data, image.content_type or "")
    return ImageOut(url=url)


@router.get("/{chapter_id}/export.md")
def export_markdown(chapter_id: int, db: DbDep) -> Response:
    chapter = chapter_service.get_chapter(db, chapter_id)
    course = course_service.require_current_course(db, chapter_id)
    content = export_service.course_markdown(chapter, course, datetime.now(UTC))
    filename = export_service.export_filename(chapter)
    return Response(
        content,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
