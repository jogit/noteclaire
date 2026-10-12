"""Recherche dans les chapitres : titre, matière, notes et cours courant (SPEC §23, FTS5)."""

import re
import unicodedata
from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import Chapter, Course

# Repères de surlignage dans les extraits : le frontend les transforme en <mark> sans v-html.
MARK_START = "\u0002"
MARK_END = "\u0003"


@dataclass(frozen=True)
class SearchResult:
    chapter_id: int
    title: str
    subject: str
    snippet: str


def index_chapter(db: Session, chapter_id: int) -> None:
    """Met à jour la ligne d'index du chapitre (à appeler après chaque modification)."""
    db.execute(text("DELETE FROM chapter_search_fts WHERE chapter_id = :id"), {"id": chapter_id})
    chapter = db.get(Chapter, chapter_id)
    if chapter is None or chapter.deleted_at is not None:
        return
    course = db.scalar(
        select(Course.content_markdown)
        .where(Course.chapter_id == chapter_id)
        .order_by(Course.version.desc())
        .limit(1)
    )
    db.execute(
        text(
            "INSERT INTO chapter_search_fts (chapter_id, title, subject, notes, course) "
            "VALUES (:id, :title, :subject, :notes, :course)"
        ),
        {
            "id": chapter_id,
            "title": chapter.title,
            "subject": chapter.subject.name,
            "notes": chapter.note.raw_text if chapter.note else "",
            "course": course or "",
        },
    )


def reindex_all(db: Session) -> None:
    db.execute(text("DELETE FROM chapter_search_fts"))
    for chapter_id in db.scalars(select(Chapter.id)):
        index_chapter(db, chapter_id)
    db.commit()


def build_query(query: str) -> str:
    """Chaque mot doit apparaître (préfixe accepté : « fonc » trouve « fonctions »)."""
    normalized = unicodedata.normalize("NFKD", query).encode("ascii", "ignore").decode().lower()
    words = re.findall(r"[a-z0-9]{2,}", normalized)
    return " AND ".join(f'"{word}"*' for word in words[:10])


def search(db: Session, student_id: int, query: str, limit: int = 20) -> list[SearchResult]:
    fts_query = build_query(query)
    if not fts_query:
        return []
    rows = db.execute(
        text(
            f"""
            SELECT chapter_id, title, subject,
                   snippet(chapter_search_fts, -1, '{MARK_START}', '{MARK_END}', '…', 16)
            FROM chapter_search_fts
            WHERE chapter_search_fts MATCH :query
              AND chapter_id IN (SELECT id FROM chapters WHERE student_id = :student_id)
            ORDER BY bm25(chapter_search_fts, 0, 10.0, 5.0, 1.0, 1.0)
            LIMIT :limit
            """
        ),
        {"query": fts_query, "student_id": student_id, "limit": limit},
    ).all()
    return [SearchResult(int(r[0]), r[1], r[2], r[3]) for r in rows]
