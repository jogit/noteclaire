"""Photo de notes manuscrites → texte.

La photo est redressée, réduite et réencodée en mémoire, ce qui supprime ses métadonnées
(EXIF, dont la position GPS) avant l'envoi à l'IA. Cette version est conservée dans
DATA_DIR/photos/<chapitre>/ pour pouvoir revoir la photo d'origine à tout moment. Le texte
obtenu est ajouté aux notes, que l'élève relit avant la mise au propre.
"""

import base64
import io
import re
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import NamedTuple

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.config import Settings
from app.errors import AppError, NotFoundError
from app.levels import adaptations_text, prompt_label
from app.prompts import PHOTO_PROMPT_VERSION
from app.services.ai.base import AIProvider, PhotoRequest, PhotoResult, UncertainSpot
from app.services.ai_runs import run_ai
from app.services.chapter_service import get_chapter
from app.services.course_service import sha256

MAX_PHOTO_BYTES = 25 * 1024 * 1024
MAX_SIDE = 2048  # suffisant pour lire une écriture manuscrite, et moins de tokens
ACCEPTED_TYPES = {"image/jpeg", "image/png", "image/webp"}
Image.MAX_IMAGE_PIXELS = 60_000_000  # protège contre les images démesurées


def prepare_image(data: bytes, max_side: int = MAX_SIDE) -> bytes:
    """Redresse (orientation EXIF), réduit et réencode en JPEG sans métadonnées."""
    try:
        with Image.open(io.BytesIO(data)) as original:
            image = ImageOps.exif_transpose(original).convert("RGB")
            image.thumbnail((max_side, max_side))
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=85, optimize=True)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise AppError("photo_unreadable", "Cette image ne peut pas être lue.", 422) from exc
    return output.getvalue()


PHOTO_NAME = re.compile(r"^[0-9a-f]{32}\.jpg$")


def chapter_photos_dir(settings: Settings, chapter_id: int) -> Path:
    return settings.data_dir / "photos" / str(chapter_id)


def save_original(settings: Settings, chapter_id: int, jpeg: bytes) -> str:
    folder = chapter_photos_dir(settings, chapter_id)
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.jpg"
    (folder / name).write_bytes(jpeg)
    return f"/api/photos/{chapter_id}/{name}"


def list_originals(settings: Settings, chapter_id: int) -> list[tuple[str, datetime]]:
    """Photos conservées du chapitre, de la plus ancienne à la plus récente."""
    folder = chapter_photos_dir(settings, chapter_id)
    if not folder.is_dir():
        return []
    files = sorted(
        (p for p in folder.iterdir() if PHOTO_NAME.match(p.name)),
        key=lambda p: p.stat().st_mtime,
    )
    return [
        (f"/api/photos/{chapter_id}/{p.name}", datetime.fromtimestamp(p.stat().st_mtime, UTC))
        for p in files
    ]


def original_path(settings: Settings, chapter_id: int, name: str) -> Path:
    if not PHOTO_NAME.match(name):  # empêche toute sortie du dossier des photos
        raise NotFoundError("Cette photo n'existe pas.")
    path = chapter_photos_dir(settings, chapter_id) / name
    if not path.is_file():
        raise NotFoundError("Cette photo n'existe pas.")
    return path


def delete_chapter_photos(settings: Settings, chapter_id: int) -> None:
    shutil.rmtree(chapter_photos_dir(settings, chapter_id), ignore_errors=True)


UNCERTAIN_MARKER = "[?]"
_SPOT = re.compile(r"\[\?\]|\[illisible\]", re.IGNORECASE)


def align_uncertain(result: PhotoResult) -> PhotoResult:
    """Un élément « uncertain » par repère [?], dans l'ordre (l'IA peut se tromper de compte).

    Un « [illisible] » écrit par l'IA devient aussi un repère, sans proposition.
    """
    items = list(result.uncertain)
    spots: list[UncertainSpot] = []

    def replace(match: re.Match[str]) -> str:
        if match.group(0) == UNCERTAIN_MARKER and items:
            spot = items.pop(0)
        else:
            spot = UncertainSpot(guess="", options=[])
        guess = spot.guess.strip()
        options = [o.strip() for o in spot.options if o.strip() and o.strip() != guess]
        spots.append(UncertainSpot(guess=guess, options=list(dict.fromkeys(options))[:3]))
        return UNCERTAIN_MARKER

    text = _SPOT.sub(replace, result.text)
    return PhotoResult(text=text, uncertain=spots)


class StoredPhotoResult(NamedTuple):
    result: PhotoResult
    url: str
    jpeg: bytes  # la photo préparée, pour la découpe des schémas


async def transcribe_photo(
    db: Session,
    settings: Settings,
    chapter_id: int,
    data: bytes,
    content_type: str,
    provider: AIProvider,
) -> StoredPhotoResult:
    chapter = get_chapter(db, chapter_id)
    if content_type.split(";")[0].strip().lower() not in ACCEPTED_TYPES:
        raise AppError("photo_unsupported", "Formats acceptés : JPEG, PNG ou WebP.", 415)
    if not data:
        raise AppError("photo_empty", "La photo est vide.")
    if len(data) > MAX_PHOTO_BYTES:
        raise AppError("photo_too_large", "La photo dépasse 25 Mo.", 413)

    jpeg = prepare_image(data)
    request = PhotoRequest(
        subject=chapter.subject.name,
        chapter=chapter.title,
        image_data_url="data:image/jpeg;base64," + base64.b64encode(jpeg).decode(),
        level=prompt_label(chapter.student.level),
        adaptations=adaptations_text(
            chapter.student.adaptation_codes, chapter.student.adaptation_notes
        ),
    )
    response, _run = await run_ai(
        db,
        settings,
        lambda: provider.transcribe_photo(request),
        chapter_id=chapter_id,
        operation="photo",
        provider=provider.name,
        model=provider.model,
        prompt_version=PHOTO_PROMPT_VERSION,
        input_hash=sha256(
            PHOTO_PROMPT_VERSION + request.adaptations + base64.b64encode(jpeg).decode()
        ),
        enforce_budget=provider.paid,
    )
    db.commit()
    result = align_uncertain(response.result)
    if not result.text.strip():
        raise AppError(
            "photo_no_text",
            "Aucun texte lisible sur cette photo. Essaie avec plus de lumière, bien à plat.",
            422,
        )
    url = save_original(settings, chapter_id, jpeg)
    return StoredPhotoResult(
        result=PhotoResult(text=result.text.strip(), uncertain=result.uncertain),
        url=url,
        jpeg=jpeg,
    )
