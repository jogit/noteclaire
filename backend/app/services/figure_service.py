"""Schémas d'une photo de notes : découpe automatique et redessin propre.

Quand la lecture d'une photo signale des schémas (« [schéma : … ] »), une seconde demande à l'IA
dit où ils sont sur la photo ; chacun est découpé et rangé avec les images du chapitre. Plus tard,
l'élève peut demander à l'IA de redessiner proprement un schéma (SVG) : c'est lui qui choisit
de garder sa photo ou le dessin propre.
"""

import base64
import io
import logging
import re
from typing import NamedTuple

from PIL import Image
from sqlalchemy.orm import Session

from app.config import Settings
from app.errors import AppError, NotFoundError
from app.prompts import FIGURES_PROMPT_VERSION, REDRAW_PROMPT_VERSION
from app.services import image_service
from app.services.ai.base import (
    AIProvider,
    FigureBox,
    FiguresRequest,
    RedrawRequest,
    RedrawResult,
)
from app.services.ai_runs import run_ai
from app.services.chapter_service import get_chapter
from app.services.course_service import sha256
from app.services.schema_drawing import draw_schema

logger = logging.getLogger(__name__)

SCHEMA_PLACEHOLDER = re.compile(r"\[sch[ée]ma\s*:\s*([^\]\n]+)\]", re.IGNORECASE)
MIN_SIDE = 40  # un rectangle plus petit (sur 1000) n'est pas un schéma
MARGIN = 15  # petit contour gardé autour du schéma (sur 1000)
CONTEXT_CHARS = 3000
SCHEMA_LINE = re.compile(r"!\[([^\]\n]*)\]\(/api/images/(\d+)/([0-9a-f]{32})\.svg\)")
STORED_IMAGE = re.compile(r"^/api/images/(\d+)/([0-9a-f]{32}\.(?:jpg|svg))$")


class CroppedFigure(NamedTuple):
    position: int  # rang du « [schéma : …] » dans le texte lu
    url: str


def _data_url(jpeg: bytes) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(jpeg).decode()


def _valid(box: FigureBox) -> bool:
    inside = all(0 <= v <= 1000 for v in (box.x_min, box.y_min, box.x_max, box.y_max))
    return inside and box.x_max - box.x_min >= MIN_SIDE and box.y_max - box.y_min >= MIN_SIDE


def _crop(jpeg: bytes, box: FigureBox) -> bytes:
    with Image.open(io.BytesIO(jpeg)) as image:
        width, height = image.size
        left = max(0, box.x_min - MARGIN) * width // 1000
        top = max(0, box.y_min - MARGIN) * height // 1000
        right = min(1000, box.x_max + MARGIN) * width // 1000
        bottom = min(1000, box.y_max + MARGIN) * height // 1000
        output = io.BytesIO()
        image.crop((left, top, right, bottom)).convert("RGB").save(
            output, format="JPEG", quality=90
        )
    return output.getvalue()


async def crop_figures(
    db: Session,
    settings: Settings,
    chapter_id: int,
    jpeg: bytes,
    text: str,
    provider: AIProvider,
) -> list[CroppedFigure]:
    """Découpe les schémas signalés dans `text`. Un échec ne doit jamais perdre le texte lu."""
    descriptions = tuple(m.strip() or "schéma" for m in SCHEMA_PLACEHOLDER.findall(text))
    if not descriptions:
        return []
    request = FiguresRequest(descriptions=descriptions, image_data_url=_data_url(jpeg))
    try:
        response, _run = await run_ai(
            db,
            settings,
            lambda: provider.locate_figures(request),
            chapter_id=chapter_id,
            operation="figures",
            provider=provider.name,
            model=provider.model,
            prompt_version=FIGURES_PROMPT_VERSION,
            input_hash=sha256(FIGURES_PROMPT_VERSION + "\n".join(descriptions) + _data_url(jpeg)),
            enforce_budget=provider.paid,
        )
        db.commit()
    except AppError as exc:  # IA indisponible, budget atteint… : on garde le texte seul
        logger.warning("figures chapter=%s error=%s", chapter_id, exc.code)
        return []
    if len(response.result.boxes) < len(descriptions):
        # Les schémas sans cadre gardent leur « [schéma : …] » dans le texte : l'élève y ajoutera
        # la photo lui-même.
        logger.info(
            "figures chapter=%s boxes=%s/%s",
            chapter_id,
            len(response.result.boxes),
            len(descriptions),
        )
    figures: list[CroppedFigure] = []
    for position, box in enumerate(response.result.boxes[: len(descriptions)]):
        if not _valid(box):
            continue
        url = image_service.save_image(settings, chapter_id, _crop(jpeg, box), "image/jpeg")
        figures.append(CroppedFigure(position, url))
    return figures


class RedrawnSchema(NamedTuple):
    url: str
    corrections: list[str]  # erreurs corrigées par l'IA ou doutes, expliqués à l'élève


def _stored_image(settings: Settings, chapter_id: int, url: str) -> bytes:
    found = STORED_IMAGE.match(url)
    if not found or int(found.group(1)) != chapter_id or found.group(2).endswith(".svg"):
        raise NotFoundError("Cette image n'existe pas.")
    return image_service.image_path(settings, chapter_id, found.group(2)).read_bytes()


def _stored_scene(settings: Settings, chapter_id: int, url: str) -> str:
    """La description d'une première version (enregistrée à côté de son SVG)."""
    found = STORED_IMAGE.match(url)
    if not found or int(found.group(1)) != chapter_id or not found.group(2).endswith(".svg"):
        raise NotFoundError("Cette image n'existe pas.")
    svg = image_service.image_path(settings, chapter_id, found.group(2))
    try:
        return svg.with_suffix(".json").read_text(encoding="utf-8")
    except OSError as exc:  # description absente : le schéma ne peut plus être corrigé
        raise NotFoundError("Cette image n'existe pas.") from exc


async def redraw_schema(
    db: Session,
    settings: Settings,
    chapter_id: int,
    image_url: str,
    provider: AIProvider,
    previous_url: str = "",
    remark: str = "",
    hand: bool = False,
) -> RedrawnSchema:
    """Redessine proprement une image du chapitre ; renvoie le SVG enregistré et les corrections.

    Avec `remark` (et `previous_url`, une première version), l'IA corrige ce que l'élève signale.
    """
    chapter = get_chapter(db, chapter_id)
    data = _stored_image(settings, chapter_id, image_url)
    with Image.open(io.BytesIO(data)) as image:
        width, height = image.size
    notes = chapter.note.raw_text if chapter.note else ""
    previous_scene = _stored_scene(settings, chapter_id, previous_url) if remark else ""
    request = RedrawRequest(
        width=width,
        height=height,
        image_data_url=_data_url(data),
        context=notes[:CONTEXT_CHARS] or "(aucune note)",
        previous_scene=previous_scene,
        remark=remark,
    )
    response, _run = await run_ai(
        db,
        settings,
        lambda: provider.redraw_schema(request),
        chapter_id=chapter_id,
        operation="redraw",
        provider=provider.name,
        model=provider.model,
        prompt_version=REDRAW_PROMPT_VERSION,
        input_hash=sha256(
            REDRAW_PROMPT_VERSION + image_url + notes[:CONTEXT_CHARS] + remark + previous_scene
        ),
        enforce_budget=provider.paid,
    )
    db.commit()
    svg = draw_schema(response.result, width, height, hand)
    url = image_service.save_svg(settings, chapter_id, svg, response.result.model_dump_json())
    return RedrawnSchema(url, response.result.corrections)


def restyle_schema(settings: Settings, chapter_id: int, svg_url: str, hand: bool) -> str:
    """Redessine un schéma déjà décrit, avec ou sans aspect manuscrit (sans rappeler l'IA)."""
    scene = RedrawResult.model_validate_json(_stored_scene(settings, chapter_id, svg_url))
    svg_name = svg_url.rsplit("/", 1)[1]
    root = image_service.image_path(settings, chapter_id, svg_name).read_text(encoding="utf-8")
    box = re.search(r'viewBox="0 0 (\d+) (\d+)"', root)
    if not box:
        raise NotFoundError("Cette image n'existe pas.")
    svg = draw_schema(scene, int(box.group(1)), int(box.group(2)), hand)
    return image_service.save_svg(settings, chapter_id, svg, scene.model_dump_json())


def describe_schemas(settings: Settings, markdown: str) -> str:
    """Remplace les schémas redessinés d'un texte par leur description, que l'IA peut lire.

    L'IA ne voit pas les images du cours : sans cela, elle ne connaît d'un schéma que sa légende.
    """

    def describe(found: re.Match[str]) -> str:
        caption, chapter_id, name = found.group(1) or "Schéma", int(found.group(2)), found.group(3)
        try:
            path = image_service.image_path(settings, chapter_id, f"{name}.svg")
            scene = RedrawResult.model_validate_json(
                path.with_suffix(".json").read_text(encoding="utf-8")
            )
        except (NotFoundError, OSError, ValueError):
            return f"[schéma : {caption}]"
        texts = " ; ".join(item.text for item in scene.texts)
        arrows = " ".join(scene.inventory)
        return f"[Schéma « {caption} ». Textes écrits : {texts}. Flèches : {arrows}]"

    return SCHEMA_LINE.sub(describe, markdown)
