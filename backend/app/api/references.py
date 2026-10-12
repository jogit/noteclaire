from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Form, UploadFile

from app.api.deps import DbDep, SettingsDep, StudentDep
from app.errors import AppError
from app.models import ReferenceDocument
from app.schemas.api import (
    DownloadReportOut,
    ReferenceDocumentContentOut,
    ReferenceDocumentOut,
    SyncReportOut,
)
from app.services import reference_catalog, reference_service

router = APIRouter(prefix="/api/references", tags=["references"])

MAX_UPLOAD_BYTES = 30 * 1024 * 1024


def document_out(document: ReferenceDocument) -> ReferenceDocumentOut:
    return ReferenceDocumentOut(
        id=document.id,
        subject_id=document.subject_id,
        title=document.title,
        source=document.source,
        url=document.url,
        school_year=document.school_year,
        file_path=document.file_path,
        chunk_count=len(document.chunks),
        updated_at=document.updated_at,
    )


@router.get("")
def list_documents(
    db: DbDep, student: StudentDep, subject_id: int | None = None
) -> list[ReferenceDocumentOut]:
    documents = reference_service.list_documents(db, student.level, subject_id)
    return [document_out(d) for d in documents]


@router.get("/{document_id}")
def get_document(document_id: int, db: DbDep) -> ReferenceDocumentContentOut:
    document = reference_service.get_document(db, document_id)
    content = "\n\n".join(
        f"## {c.heading}\n\n{c.content}" if c.heading else c.content for c in document.chunks
    )
    return ReferenceDocumentContentOut(**document_out(document).model_dump(), content=content)


@router.post("", status_code=201)
async def upload_document(
    file: UploadFile,
    db: DbDep,
    settings: SettingsDep,
    student: StudentDep,
    subject_id: Annotated[int, Form()],
    title: Annotated[str, Form()] = "",
    source: Annotated[str, Form()] = "",
    url: Annotated[str, Form()] = "",
) -> ReferenceDocumentOut:
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise AppError("reference_too_large", "Le fichier dépasse 30 Mo.", 413)
    document = reference_service.save_upload(
        db,
        settings,
        subject_id,
        student.level,
        file.filename or "document",
        data,
        {"title": title, "source": source, "url": url},
    )
    return document_out(document)


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: int, db: DbDep, settings: SettingsDep) -> None:
    reference_service.delete_document(db, settings, document_id)


@router.post("/sync")
def sync(db: DbDep, settings: SettingsDep) -> SyncReportOut:
    return SyncReportOut(**asdict(reference_service.sync_references(db, settings)))


@router.post("/download")
def download_official_programmes(
    db: DbDep, settings: SettingsDep, student: StudentDep
) -> DownloadReportOut:
    """Télécharge les programmes officiels de la classe de l'élève (à la demande)."""
    report = reference_catalog.download_catalog(db, settings, student.level)
    return DownloadReportOut(**asdict(report))
