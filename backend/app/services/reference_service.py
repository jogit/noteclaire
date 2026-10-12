"""Documents de référence : import depuis le dossier, découpage et recherche FTS5 (SPEC §20).

Le dossier `DATA_DIR/references/<classe>/<matière>/` est la source de vérité : la base n'est
qu'un index, reconstruit par `sync_references`. Formats : .md, .txt, .pdf.
Métadonnées facultatives : en-tête `---` (Markdown) ou fichier voisin `<nom>.meta.json`.
"""

import hashlib
import json
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.errors import AppError, NotFoundError
from app.levels import LEVEL_IDS
from app.models import ReferenceChunk, ReferenceDocument, Subject

logger = logging.getLogger(__name__)

SUPPORTED_SUFFIXES = {".md", ".txt", ".pdf"}
META_SUFFIX = ".meta.json"
CHUNK_CHARS = 1200


def references_root(settings: Settings) -> Path:
    return settings.data_dir / "references"


@dataclass
class SyncReport:
    added: int = 0
    updated: int = 0
    removed: int = 0
    unchanged: int = 0
    errors: list[str] = field(default_factory=list)


# --- Lecture des fichiers ---------------------------------------------------------------


def _read_metadata(path: Path) -> tuple[dict[str, str], str | None]:
    """Renvoie (métadonnées, texte Markdown sans en-tête si fichier texte)."""
    meta: dict[str, str] = {}
    sidecar = path.with_name(path.name + META_SUFFIX)
    if sidecar.exists():
        raw = json.loads(sidecar.read_text(encoding="utf-8"))
        meta.update({k: str(v) for k, v in raw.items() if v is not None})

    if path.suffix == ".pdf":
        return meta, None

    content = path.read_text(encoding="utf-8", errors="replace")
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.S)
    if match:
        for line in match.group(1).splitlines():
            key, sep, value = line.partition(":")
            if sep:
                meta.setdefault(key.strip(), value.strip().strip("\"'"))
        content = content[match.end() :]
    return meta, content


def _pdf_text(path: Path) -> str:
    from pypdf import PdfReader  # import local : dépendance lourde, utile seulement ici

    reader = PdfReader(path)
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(pages)


def _default_title(path: Path) -> str:
    title = re.sub(r"[-_]+", " ", path.stem).strip()
    return title[:1].upper() + title[1:] if title else path.name


# --- Découpage ---------------------------------------------------------------------------


def split_chunks(content: str, max_chars: int = CHUNK_CHARS) -> list[tuple[str, str]]:
    """Découpe en extraits (titre de section, texte) d'au plus ~max_chars caractères."""
    chunks: list[tuple[str, str]] = []
    heading = ""
    buffer: list[str] = []

    def flush() -> None:
        body = "\n\n".join(buffer).strip()
        if body:
            chunks.append((heading, body))
        buffer.clear()

    blocks = re.split(r"\n\s*\n", content.replace("\r\n", "\n"))
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        heading_match = re.match(r"^#{1,6}\s+(.+)", block)
        if heading_match:
            flush()
            heading = heading_match.group(1).strip()[:300]
            rest = block[heading_match.end() :].strip()
            if rest:
                buffer.append(rest)
            continue
        for piece in _split_long(block, max_chars):
            if buffer and sum(len(b) for b in buffer) + len(piece) > max_chars:
                flush()
            buffer.append(piece)
    flush()
    return chunks


def _split_long(block: str, max_chars: int) -> list[str]:
    """Coupe un bloc trop long aux fins de ligne, puis de phrase."""
    if len(block) <= max_chars:
        return [block]
    pieces: list[str] = []
    current = ""
    for unit in re.split(r"(?<=[.!?:;])\s+|\n", block):
        if current and len(current) + len(unit) + 1 > max_chars:
            pieces.append(current)
            current = ""
        current = f"{current} {unit}".strip()
        while len(current) > max_chars:
            pieces.append(current[:max_chars])
            current = current[max_chars:]
    if current:
        pieces.append(current)
    return pieces


# --- Synchronisation ---------------------------------------------------------------------


def _content_hash(path: Path) -> str:
    """Empreinte du fichier et de ses métadonnées voisines : change si l'un des deux change."""
    digest = hashlib.sha256(path.read_bytes())
    sidecar = path.with_name(path.name + META_SUFFIX)
    if sidecar.exists():
        digest.update(sidecar.read_bytes())
    return digest.hexdigest()


def _locate(path: Path, root: Path, subjects: dict[str, Subject]) -> tuple[str, str, Subject]:
    """(chemin relatif, classe, matière) d'un fichier ; ValueError si le dossier est inconnu."""
    relative = path.relative_to(root).as_posix()
    level = path.parent.parent.name
    if level not in LEVEL_IDS:
        raise ValueError(f"{relative} : classe inconnue")
    subject = subjects.get(path.parent.name)
    if subject is None:
        raise ValueError(f"{relative} : matière inconnue")
    return relative, level, subject


def sync_references(db: Session, settings: Settings) -> SyncReport:
    """Met l'index en accord avec le dossier des références. Idempotent."""
    report = SyncReport()
    root = references_root(settings)
    subjects = {s.slug: s for s in db.scalars(select(Subject))}
    existing = {d.file_path: d for d in db.scalars(select(ReferenceDocument))}
    seen: set[str] = set()

    files = sorted(root.glob("*/*/*")) if root.exists() else []
    for path in files:
        if path.suffix.lower() not in SUPPORTED_SUFFIXES or not path.is_file():
            continue
        try:
            relative, level, subject = _locate(path, root, subjects)
        except ValueError as exc:
            report.errors.append(str(exc))
            continue
        seen.add(relative)
        file_hash = _content_hash(path)
        document = existing.get(relative)
        if document is not None and document.file_hash == file_hash:
            report.unchanged += 1
            continue
        try:
            with db.begin_nested():  # annule ce seul fichier s'il est illisible
                _index_file(db, path, relative, file_hash, subject, level, document)
        except Exception as exc:  # fichier illisible : on le signale sans bloquer les autres
            logger.warning("reference %s: %s", relative, type(exc).__name__)
            report.errors.append(f"{relative} : lecture impossible ({type(exc).__name__})")
            continue
        if document is None:
            report.added += 1
        else:
            report.updated += 1

    for relative, document in existing.items():
        if relative not in seen:
            db.delete(document)
            report.removed += 1
    db.commit()
    logger.info(
        "references sync added=%s updated=%s removed=%s unchanged=%s errors=%s",
        report.added,
        report.updated,
        report.removed,
        report.unchanged,
        len(report.errors),
    )
    return report


def _index_file(
    db: Session,
    path: Path,
    relative: str,
    file_hash: str,
    subject: Subject,
    level: str,
    document: ReferenceDocument | None,
) -> None:
    meta, content = _read_metadata(path)
    if content is None:
        content = _pdf_text(path)
    chunks = split_chunks(content)
    if not chunks:
        raise ValueError("document vide")

    if document is None:
        document = ReferenceDocument(file_path=relative, subject_id=subject.id)
        db.add(document)
    document.title = meta.get("title") or _default_title(path)
    document.source = meta.get("source", "")
    document.url = meta.get("url", "")
    document.school_year = meta.get("school_year", "")
    document.level = level
    document.file_hash = file_hash
    document.chunks = [
        ReferenceChunk(position=i, heading=heading, content=body)
        for i, (heading, body) in enumerate(chunks)
    ]
    db.flush()


# --- Gestion des fichiers (API) ------------------------------------------------------------


def safe_filename(name: str) -> str:
    stem, suffix = Path(name).stem, Path(name).suffix.lower()
    ascii_stem = unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^A-Za-z0-9]+", "-", ascii_stem).strip("-").lower() or "document"
    return f"{slug[:80]}{suffix}"


def save_upload(
    db: Session,
    settings: Settings,
    subject_id: int,
    level: str,
    filename: str,
    data: bytes,
    metadata: dict[str, str],
) -> ReferenceDocument:
    subject = db.get(Subject, subject_id)
    if subject is None:
        raise AppError("unknown_subject", "Cette matière n'existe pas.", 422)
    if Path(filename).suffix.lower() not in SUPPORTED_SUFFIXES:
        raise AppError(
            "reference_unsupported", "Formats acceptés : PDF, Markdown (.md) ou texte (.txt).", 415
        )
    if not data:
        raise AppError("reference_empty", "Le fichier est vide.")

    if level not in LEVEL_IDS:
        raise AppError("unknown_level", "Cette classe n'existe pas.", 422)
    folder = references_root(settings) / level / subject.slug
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / safe_filename(filename)
    counter = 2
    while target.exists():
        target = folder / f"{Path(safe_filename(filename)).stem}-{counter}{target.suffix}"
        counter += 1
    target.write_bytes(data)
    clean_meta = {k: v.strip() for k, v in metadata.items() if v and v.strip()}
    if clean_meta:
        sidecar = target.with_name(target.name + META_SUFFIX)
        sidecar.write_text(json.dumps(clean_meta, ensure_ascii=False, indent=2), encoding="utf-8")

    report = sync_references(db, settings)
    relative = target.relative_to(references_root(settings)).as_posix()
    document = db.scalar(select(ReferenceDocument).where(ReferenceDocument.file_path == relative))
    if document is None:
        target.unlink(missing_ok=True)
        target.with_name(target.name + META_SUFFIX).unlink(missing_ok=True)
        detail = next((e for e in report.errors if e.startswith(relative)), "")
        raise AppError("reference_unreadable", f"Impossible de lire ce document. {detail}", 422)
    return document


def delete_document(db: Session, settings: Settings, document_id: int) -> None:
    document = get_document(db, document_id)
    path = references_root(settings) / document.file_path
    path.unlink(missing_ok=True)
    path.with_name(path.name + META_SUFFIX).unlink(missing_ok=True)
    db.delete(document)
    db.commit()


def get_document(db: Session, document_id: int) -> ReferenceDocument:
    document = db.get(ReferenceDocument, document_id)
    if document is None:
        raise NotFoundError("Ce document n'existe pas.")
    return document


def list_documents(db: Session, level: str, subject_id: int | None) -> list[ReferenceDocument]:
    query = (
        select(ReferenceDocument)
        .where(ReferenceDocument.level == level)
        .order_by(ReferenceDocument.title)
    )
    if subject_id is not None:
        query = query.where(ReferenceDocument.subject_id == subject_id)
    return list(db.scalars(query))
