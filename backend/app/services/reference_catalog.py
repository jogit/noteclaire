"""Programmes officiels : téléchargés à la demande depuis les adresses du catalogue.

Le dépôt ne contient aucun document officiel, seulement leurs adresses
(`data/references_catalog.json`). Rien n'est téléchargé sans action de l'utilisateur.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from app.config import Settings
from app.services.reference_service import (
    META_SUFFIX,
    references_root,
    safe_filename,
    sync_references,
)

logger = logging.getLogger(__name__)

CATALOG_FILE = Path(__file__).parent.parent / "data" / "references_catalog.json"
MAX_BYTES = 40 * 1024 * 1024


@dataclass
class DownloadReport:
    downloaded: int = 0
    already: int = 0
    errors: list[str] = field(default_factory=list)


def catalog_entries_all() -> list[dict[str, str]]:
    entries: list[dict[str, str]] = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
    return entries


def catalog_entries(level: str) -> list[dict[str, str]]:
    return [e for e in catalog_entries_all() if e["level"] == level]


def _client() -> httpx.Client:
    return httpx.Client(follow_redirects=True, timeout=30, headers={"User-Agent": "NoteClaire"})


def _fetch_pdf(client: httpx.Client, url: str) -> bytes:
    """Télécharge un PDF (taille limitée) ; ValueError si ce n'en est pas un."""
    data = bytearray()
    with client.stream("GET", url) as response:
        response.raise_for_status()
        for chunk in response.iter_bytes():
            data.extend(chunk)
            if len(data) > MAX_BYTES:
                raise ValueError("fichier trop gros")
    if not data.startswith(b"%PDF"):
        raise ValueError("ce n'est pas un PDF")
    return bytes(data)


def download_catalog(db: Session, settings: Settings, level: str) -> DownloadReport:
    """Télécharge les programmes de la classe qui manquent, puis met l'index à jour."""
    report = DownloadReport()
    fetched: dict[str, bytes] = {}  # un même PDF sert à plusieurs matières (langues vivantes)
    with _client() as client:
        for entry in catalog_entries(level):
            folder = references_root(settings) / level / entry["subject"]
            target = folder / safe_filename(entry["title"] + ".pdf")
            if target.exists():
                report.already += 1
                continue
            try:
                if entry["url"] not in fetched:
                    fetched[entry["url"]] = _fetch_pdf(client, entry["url"])
            except (httpx.HTTPError, ValueError) as exc:
                logger.warning("catalogue %s : %s", entry["url"], type(exc).__name__)
                report.errors.append(f"{entry['title']} : téléchargement impossible ({exc})")
                continue
            folder.mkdir(parents=True, exist_ok=True)
            target.write_bytes(fetched[entry["url"]])
            meta = {k: entry[k] for k in ("title", "source", "url", "school_year") if entry.get(k)}
            target.with_name(target.name + META_SUFFIX).write_text(
                json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            report.downloaded += 1
    sync_references(db, settings)
    return report
