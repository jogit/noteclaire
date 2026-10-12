"""Recherche des extraits de référence utiles à l'analyse d'un cours (SQLite FTS5).

L'indexation des documents est dans `reference_service`.
"""

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

CONTEXT_CHUNKS = 6
CONTEXT_MAX_CHARS = 7000
QUERY_TERMS = 30

# Mots trop fréquents pour aider la recherche.
_STOPWORDS_TEXT = """
    alors aussi autre autres avant avec avoir bien cela celle celles celui ceux cette chaque
    comme comment dans depuis donc dont elle elles entre est etre etait fait faire font hors
    leur leurs lors mais meme moins notre nous par parce pendant peut plus pour pourquoi
    quand quel quelle quelles quels sans selon sera sont sous sur tous tout toute toutes
    tres une vers votre vous ainsi encore apres ici cours chapitre exemple exemples
    definition note notes
"""
STOPWORDS = frozenset(_STOPWORDS_TEXT.split())


@dataclass(frozen=True)
class ReferenceExcerpt:
    document_title: str
    source: str
    heading: str
    content: str


def _normalize(word: str) -> str:
    return unicodedata.normalize("NFKD", word).encode("ascii", "ignore").decode().lower()


def build_query(text_: str, max_terms: int = QUERY_TERMS) -> str:
    """Requête FTS5 : les mots les plus fréquents et significatifs, reliés par OR."""
    words = [_normalize(w) for w in re.findall(r"[^\W\d_]{4,}", text_)]
    counts = Counter(w for w in words if w not in STOPWORDS)
    terms = [word for word, _ in counts.most_common(max_terms)]
    return " OR ".join(f'"{term}"' for term in terms)


def search_references(
    db: Session, subject_id: int, level: str, text_: str, limit: int = CONTEXT_CHUNKS
) -> list[ReferenceExcerpt]:
    query = build_query(text_)
    if not query:
        return []
    rows = db.execute(
        text(
            """
            SELECT d.title, d.source, c.heading, c.content
            FROM reference_chunks_fts
            JOIN reference_chunks c ON c.id = reference_chunks_fts.rowid
            JOIN reference_documents d ON d.id = c.document_id
            WHERE reference_chunks_fts MATCH :query AND d.subject_id = :subject_id
              AND d.level = :level
            ORDER BY bm25(reference_chunks_fts, 2.0, 1.0)
            LIMIT :limit
            """
        ),
        {"query": query, "subject_id": subject_id, "level": level, "limit": limit},
    ).all()
    return [ReferenceExcerpt(*row) for row in rows]


def format_context(excerpts: list[ReferenceExcerpt], max_chars: int = CONTEXT_MAX_CHARS) -> str:
    """Texte des extraits fourni à l'IA, chacun avec le titre exact de son document."""
    parts: list[str] = []
    total = 0
    for excerpt in excerpts:
        header = f'### Document : "{excerpt.document_title}"'
        if excerpt.source:
            header += f" (source : {excerpt.source})"
        if excerpt.heading:
            header += f"\nSection : {excerpt.heading}"
        part = f"{header}\n{excerpt.content}"
        if total + len(part) > max_chars:
            break
        parts.append(part)
        total += len(part)
    return "\n\n".join(parts)
