"""Images du cours (schémas photographiés…), rangées par chapitre dans DATA_DIR/images/.

Comme les photos de notes, elles sont redressées, réduites et réencodées sans métadonnées.
"""

import re
import shutil
import uuid
from pathlib import Path

from app.config import Settings
from app.errors import AppError, NotFoundError
from app.services.photo_service import ACCEPTED_TYPES, MAX_PHOTO_BYTES, prepare_image

IMAGE_NAME = re.compile(r"^[0-9a-f]{32}\.(jpg|svg)$")
COURSE_IMAGE_SIDE = 1600


def chapter_images_dir(settings: Settings, chapter_id: int) -> Path:
    return settings.data_dir / "images" / str(chapter_id)


def save_image(settings: Settings, chapter_id: int, data: bytes, content_type: str) -> str:
    if content_type.split(";")[0].strip().lower() not in ACCEPTED_TYPES:
        raise AppError("photo_unsupported", "Formats acceptés : JPEG, PNG ou WebP.", 415)
    if not data:
        raise AppError("photo_empty", "L'image est vide.")
    if len(data) > MAX_PHOTO_BYTES:
        raise AppError("photo_too_large", "L'image dépasse 25 Mo.", 413)
    jpeg = prepare_image(data, max_side=COURSE_IMAGE_SIDE)
    folder = chapter_images_dir(settings, chapter_id)
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.jpg"
    (folder / name).write_bytes(jpeg)
    return f"/api/images/{chapter_id}/{name}"


def save_svg(settings: Settings, chapter_id: int, svg: str, scene: str) -> str:
    """Enregistre un schéma redessiné, avec sa description (pour pouvoir le corriger ensuite)."""
    folder = chapter_images_dir(settings, chapter_id)
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.svg"
    (folder / name).write_text(svg, encoding="utf-8")
    (folder / name).with_suffix(".json").write_text(scene, encoding="utf-8")
    return f"/api/images/{chapter_id}/{name}"


def image_path(settings: Settings, chapter_id: int, name: str) -> Path:
    if not IMAGE_NAME.match(name):  # empêche toute sortie du dossier des images
        raise NotFoundError("Cette image n'existe pas.")
    path = chapter_images_dir(settings, chapter_id) / name
    if not path.is_file():
        raise NotFoundError("Cette image n'existe pas.")
    return path


def delete_chapter_images(settings: Settings, chapter_id: int) -> None:
    shutil.rmtree(chapter_images_dir(settings, chapter_id), ignore_errors=True)
