"""Export du cours (SPEC §24). Le PDF est produit par le navigateur (vue d'impression)."""

import html
import re
import unicodedata
from datetime import datetime

from app.models import Chapter, Course
from app.services.ai.base import QuizQuestion

ORIGINS = {
    "ai_structure": "mis au propre",
    "user_edit": "modifié à la main",
    "suggestion_applied": "suggestion acceptée",
}


def course_markdown(chapter: Chapter, course: Course, exported_at: datetime) -> str:
    header = (
        f"<!-- NoteClaire — {chapter.subject.name} — {chapter.title} — "
        f"version {course.version} ({ORIGINS.get(course.origin, course.origin)}) — "
        f"exporté le {exported_at:%d/%m/%Y} -->\n\n"
        f"**{chapter.subject.name}** · {chapter.title} · {exported_at:%d/%m/%Y}\n\n"
    )
    return header + course.content_markdown.strip() + "\n"


def export_filename(chapter: Chapter, suffix: str = ".md") -> str:
    ascii_title = (
        unicodedata.normalize("NFKD", f"{chapter.subject.slug}-{chapter.title}")
        .encode("ascii", "ignore")
        .decode()
    )
    slug = re.sub(r"[^A-Za-z0-9]+", "-", ascii_title).strip("-").lower() or "cours"
    return f"{slug[:80]}{suffix}"


def _anki_field(text: str) -> str:
    """Texte d'une carte Anki : HTML échappé, retours à la ligne en <br>, sans tabulation."""
    return html.escape(text.strip(), quote=False).replace("\t", " ").replace("\n", "<br>")


def anki_text(chapter: Chapter, questions: list[QuizQuestion]) -> str:
    """Quiz au format d'import texte d'Anki : une carte par question, champs séparés par une
    tabulation (recto, verso, étiquette). Fichier → Importer dans Anki ; le paquet est choisi
    par l'en-tête `#deck` (Anki 2.1.54 et plus) ou dans la fenêtre d'import."""
    lines = [
        "#separator:tab",
        "#html:true",
        "#tags column:3",
        f"#deck:NoteClaire::{chapter.subject.name}::{chapter.title}".replace("\t", " "),
    ]
    tag = chapter.subject.slug
    for question in questions:
        front = _anki_field(question.question)
        if question.choices:
            front += "<br><br>" + "<br>".join(f"• {_anki_field(c)}" for c in question.choices)
        back = f"<b>{_anki_field(question.answer)}</b>"
        if question.explanation.strip():
            back += "<br><br>" + _anki_field(question.explanation)
        if question.course_excerpt.strip():
            back += "<br><br>Dans ton cours : « " + _anki_field(question.course_excerpt) + " »"
        lines.append("\t".join([front, back, tag]))
    return "\n".join(lines) + "\n"
