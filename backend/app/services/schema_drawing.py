"""Dessin propre (SVG) d'un schéma décrit par l'IA.

L'IA ne produit jamais de SVG : elle décrit des textes, des flèches (avec, pour chacune, « pointe
au début ? pointe à la fin ? ») et des traits. Ce module vérifie cette description et en fait le
SVG : les pointes de flèche sont donc toujours celles demandées, et le résultat ne contient que ce
que nous avons décidé d'écrire (pas de script, de lien ni de balise inattendue).
"""

import base64
import math
import re
from functools import cache
from pathlib import Path
from xml.sax.saxutils import escape

from app.errors import AppError
from app.services.ai.base import RedrawResult

COLORS = {"noir": "#1d2233", "bleu": "#2c3fb8", "vert": "#1f8a3d", "rouge": "#c62828"}
# Police manuscrite (Caveat, licence SIL OFL) : intégrée au SVG, qui est affiché comme une image.
HAND_FONT = Path(__file__).resolve().parent.parent / "assets" / "caveat.woff2"
HAND_SCALE = 1.2  # Caveat a de petites lettres
# Léger tremblé des traits, pour un aspect dessiné à la main.
WOBBLE = (
    '<filter id="tremble"><feTurbulence type="fractalNoise" baseFrequency="0.03" numOctaves="2" '
    'seed="3"/><feDisplacementMap in="SourceGraphic" scale="3"/></filter>'
)
STROKE_WIDTH = 2.5
MAX_ELEMENTS = 300
MIN_SIZE, MAX_SIZE = 12.0, 80.0
# Un tracé ne contient que des commandes de dessin, des nombres et des séparateurs.
PATH = re.compile(r"[MmLlHhVvCcSsQqTtAaZz0-9eE.,\s+-]{1,3000}")
MARKUP = re.compile(r"(_\{[^{}]*\}|\^\{[^{}]*\})")


def _arrowhead(color: str) -> str:
    return (
        f'<marker id="pointe-{color[1:]}" markerWidth="12" markerHeight="10" refX="10" refY="5" '
        'orient="auto-start-reverse" markerUnits="userSpaceOnUse">'
        f'<path d="M 0 0 L 12 5 L 0 10 z" fill="{color}"/></marker>'
    )


@cache
def _hand_font_css() -> str:
    data = base64.b64encode(HAND_FONT.read_bytes()).decode()
    return (
        f"@font-face{{font-family:Caveat;src:url(data:font/woff2;base64,{data}) format('woff2')}}"
    )


def _invalid() -> AppError:
    return AppError("schema_invalid", "Le schéma redessiné est inutilisable.", 502)


def _number(value: float) -> float:
    if not math.isfinite(value):
        raise _invalid()
    return round(value, 1)


def _path(d: str) -> str:
    if not PATH.fullmatch(d.strip()):
        raise _invalid()
    return escape(d.strip(), {'"': "&quot;"})


def _text(text: str, size: float) -> str:
    """Texte avec indices et exposants : « Ca(OH)_{2} », « Ca^{2+} »."""
    small = round(size * 0.7, 1)
    shift = round(size * 0.35, 1)
    parts: list[str] = []
    offset = 0.0  # décalage vertical courant, à annuler en revenant au texte normal
    for piece in MARKUP.split(text):
        if not piece:
            continue
        if piece[0] in "_^" and piece[1:2] == "{":
            target = shift if piece[0] == "_" else -shift
            dy = target - offset
            offset = target
            parts.append(f'<tspan dy="{dy}" font-size="{small}">{escape(piece[2:-1])}</tspan>')
        else:
            dy = -offset
            offset = 0.0
            parts.append(f'<tspan dy="{dy}">{escape(piece)}</tspan>' if dy else escape(piece))
    return "".join(parts)


def draw_schema(scene: RedrawResult, width: int, height: int, hand: bool = False) -> str:
    """Le SVG de la description ; AppError("schema_invalid") si elle est inutilisable.

    `hand` : police et traits à l'aspect manuscrit (les couleurs sont celles de l'élève dans les
    deux cas).
    """
    total = len(scene.texts) + len(scene.arrows) + len(scene.lines)
    if total == 0 or total > MAX_ELEMENTS or width < 1 or height < 1:
        raise _invalid()
    caps = 'stroke-linecap="round" stroke-linejoin="round"'
    used: set[str] = set()
    body: list[str] = []

    def strokes(color: str) -> str:
        return f'fill="none" stroke="{color}" stroke-width="{STROKE_WIDTH}" {caps}'

    for line in scene.lines:
        body.append(f'<path d="{_path(line.d)}" {strokes(COLORS[line.color])}/>')
    for arrow in scene.arrows:
        color = COLORS[arrow.color]
        used.add(color)
        marker = f"url(#pointe-{color[1:]})"
        heads = f' marker-start="{marker}"' if arrow.head_start else ""
        heads += f' marker-end="{marker}"' if arrow.head_end else ""
        body.append(f'<path d="{_path(arrow.d)}" {strokes(color)}{heads}/>')
    for item in scene.texts:
        size = min(max(_number(item.size), MIN_SIZE), MAX_SIZE)
        size = round(size * HAND_SCALE, 1) if hand else size
        body.append(
            f'<text x="{_number(item.x)}" y="{_number(item.y)}" font-size="{size}" '
            f'fill="{COLORS[item.color]}">{_text(item.text, size)}</text>'
        )
    defs = "".join(_arrowhead(color) for color in sorted(used))
    family = "Caveat, cursive" if hand else "sans-serif"
    drawing = f'<g font-family="{family}">{"".join(body)}</g>'
    if hand:
        defs += f"{WOBBLE}<style>{_hand_font_css()}</style>"
        drawing = f'<g filter="url(#tremble)">{drawing}</g>'
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">'
        f"<defs>{defs}</defs>{drawing}</svg>"
    )
