"""Sauvegardes : une archive zip par jour (base de données + images), les 7 dernières gardées.

Les jetons ChatGPT (data/secrets/) ne sont jamais sauvegardés.
"""

import asyncio
import logging
import re
import shutil
import sqlite3
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.config import Settings
from app.errors import AppError, NotFoundError

logger = logging.getLogger("app.backup")

BACKUP_NAME = re.compile(r"^noteclaire-\d{8}-\d{6}\.zip$")
BACKUP_INTERVAL = timedelta(hours=24)
CHECK_EVERY_SECONDS = 3600


@dataclass(frozen=True)
class BackupInfo:
    name: str
    size: int
    created_at: datetime


def list_backups(settings: Settings) -> list[BackupInfo]:
    folder = settings.backup_dir
    if not folder.is_dir():
        return []
    backups = [
        BackupInfo(p.name, p.stat().st_size, datetime.fromtimestamp(p.stat().st_mtime, UTC))
        for p in folder.iterdir()
        if p.is_file() and BACKUP_NAME.match(p.name)
    ]
    return sorted(backups, key=lambda b: b.name, reverse=True)


def backup_path(settings: Settings, name: str) -> Path:
    if not BACKUP_NAME.match(name):  # empêche toute sortie du dossier des sauvegardes
        raise NotFoundError("Cette sauvegarde n'existe pas.")
    path = settings.backup_dir / name
    if not path.is_file():
        raise NotFoundError("Cette sauvegarde n'existe pas.")
    return path


def create_backup(settings: Settings, engine: Engine) -> BackupInfo:
    """Copie cohérente de la base (sauvegarde en ligne SQLite) et des images dans un zip."""
    folder = settings.backup_dir
    folder.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC)
    while (folder / f"noteclaire-{now:%Y%m%d-%H%M%S}.zip").exists():
        now += timedelta(seconds=1)  # jamais d'écrasement d'une sauvegarde existante
    name = f"noteclaire-{now:%Y%m%d-%H%M%S}.zip"
    target = folder / name
    partial = folder / f".{name}.part"
    with tempfile.TemporaryDirectory() as tmp:
        db_copy = Path(tmp) / "app.db"
        source = engine.raw_connection()
        try:
            destination = sqlite3.connect(db_copy)
            try:
                source.driver_connection.backup(destination)  # type: ignore[union-attr]
            finally:
                destination.close()
        finally:
            source.close()
        with zipfile.ZipFile(partial, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.write(db_copy, "app.db")
            for folder_name in ("images", "photos"):
                source_dir = settings.data_dir / folder_name
                for path in sorted(source_dir.rglob("*")) if source_dir.is_dir() else []:
                    if path.is_file():
                        archive.write(
                            path, (Path(folder_name) / path.relative_to(source_dir)).as_posix()
                        )
    partial.replace(target)
    prune(settings)
    logger.info("sauvegarde créée : %s", name)
    return next(b for b in list_backups(settings) if b.name == name)


IMAGE_FOLDERS = ("images", "photos")
MAX_RESTORED_BYTES = 8 * 1024**3  # taille décompressée : protège d'une archive piégée


def _archive_members(archive: zipfile.ZipFile) -> list[str]:
    """Fichiers de l'archive, après vérification qu'elle a bien la forme d'une sauvegarde."""
    names = [n for n in archive.namelist() if not n.endswith("/")]
    allowed = tuple(f"{folder}/" for folder in IMAGE_FOLDERS)
    for name in names:
        if ".." in Path(name).parts or not (name == "app.db" or name.startswith(allowed)):
            raise AppError(
                "backup_invalid", "Ce fichier n'est pas une sauvegarde de NoteClaire.", 422
            )
    if "app.db" not in names:
        raise AppError("backup_invalid", "Ce fichier n'est pas une sauvegarde de NoteClaire.", 422)
    if sum(info.file_size for info in archive.infolist()) > MAX_RESTORED_BYTES:
        raise AppError("backup_too_large", "Cette sauvegarde est trop volumineuse.", 413)
    return names


def _schema_version(connection: sqlite3.Connection) -> str | None:
    try:
        row = connection.execute("SELECT version_num FROM alembic_version").fetchone()
    except sqlite3.DatabaseError:
        return None
    return str(row[0]) if row else None


def _check_database(copy: Path, engine: Engine) -> None:
    """La base de l'archive doit être intacte et de la même version que l'application."""
    connection = sqlite3.connect(copy)
    try:
        intact = connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        version = _schema_version(connection)
    except sqlite3.DatabaseError:
        intact, version = False, None
    finally:
        connection.close()
    if not intact:
        raise AppError("backup_invalid", "Cette sauvegarde est abîmée.", 422)
    with engine.connect() as live:
        current = live.execute(text("SELECT version_num FROM alembic_version")).scalar()
    if version != current:
        raise AppError(
            "backup_incompatible", "Cette sauvegarde vient d'une autre version de NoteClaire.", 422
        )


def restore_backup(settings: Settings, engine: Engine, archive_path: Path) -> None:
    """Remplace la base et les images par celles de l'archive.

    Tout est vérifié avant de toucher aux données, puis l'état actuel est sauvegardé : une
    restauration se défait en restaurant la copie de sécurité.
    """
    try:
        archive = zipfile.ZipFile(archive_path)
    except zipfile.BadZipFile as exc:
        raise AppError(
            "backup_invalid", "Ce fichier n'est pas une sauvegarde de NoteClaire.", 422
        ) from exc
    with archive, tempfile.TemporaryDirectory() as tmp:
        names = _archive_members(archive)
        database = Path(archive.extract("app.db", tmp))
        _check_database(database, engine)
        create_backup(settings, engine)  # copie de sécurité de l'état actuel

        source = sqlite3.connect(database)
        destination = engine.raw_connection()
        try:
            source.backup(destination.driver_connection)  # type: ignore[arg-type]
        finally:
            source.close()
            destination.close()
        engine.dispose()

        for folder in IMAGE_FOLDERS:
            shutil.rmtree(settings.data_dir / folder, ignore_errors=True)
        for name in names:
            if name != "app.db":
                archive.extract(name, settings.data_dir)
    logger.info("sauvegarde restaurée : %s", archive_path.name)


def prune(settings: Settings) -> None:
    for old in list_backups(settings)[settings.backup_keep :]:
        (settings.backup_dir / old.name).unlink(missing_ok=True)


def backup_due(settings: Settings, now: datetime | None = None) -> bool:
    backups = list_backups(settings)
    now = now or datetime.now(UTC)
    return not backups or now - backups[0].created_at >= BACKUP_INTERVAL


async def run_scheduler(settings: Settings, engine: Engine) -> None:
    """Vérifie toutes les heures s'il faut faire la sauvegarde du jour."""
    while True:
        try:
            if backup_due(settings):
                await asyncio.to_thread(create_backup, settings, engine)
        except Exception:  # une sauvegarde ratée ne doit pas arrêter l'application
            logger.exception("la sauvegarde automatique a échoué")
        await asyncio.sleep(CHECK_EVERY_SECONDS)
