import tempfile
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.api.deps import SettingsDep
from app.errors import AppError
from app.services import backup_service

router = APIRouter(prefix="/api/backups", tags=["backups"])

MAX_UPLOAD_BYTES = 2 * 1024 * 1024 * 1024


class BackupOut(BaseModel):
    name: str
    size: int
    created_at: datetime


@router.get("")
def list_backups(settings: SettingsDep) -> list[BackupOut]:
    return [BackupOut(**vars(b)) for b in backup_service.list_backups(settings)]


@router.post("", status_code=201)
def create_backup(request: Request, settings: SettingsDep) -> BackupOut:
    info = backup_service.create_backup(settings, request.app.state.db.engine)
    return BackupOut(**vars(info))


@router.get("/{name}")
def download_backup(name: str, settings: SettingsDep) -> FileResponse:
    path = backup_service.backup_path(settings, name)
    return FileResponse(path, media_type="application/zip", filename=name)


@router.post("/{name}/restore", status_code=204)
def restore_backup(name: str, request: Request, settings: SettingsDep) -> None:
    """Remplace toutes les données par celles de cette sauvegarde (copie de sécurité avant)."""
    path = backup_service.backup_path(settings, name)
    backup_service.restore_backup(settings, request.app.state.db.engine, path)


@router.post("/restore", status_code=204)
async def restore_uploaded_backup(
    file: UploadFile, request: Request, settings: SettingsDep
) -> None:
    """Idem avec un fichier de sauvegarde envoyé depuis l'ordinateur (autre installation)."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "upload.zip"
        size = 0
        with path.open("wb") as out:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise AppError("backup_too_large", "Ce fichier est trop gros.", 413)
                out.write(chunk)
        backup_service.restore_backup(settings, request.app.state.db.engine, path)
