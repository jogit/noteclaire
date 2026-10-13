"""Contrôle de la mise au propre : le cours produit doit rester celui des notes de l'élève.

Le prompt interdit de reformuler, résumer ou compléter ; ce contrôle le vérifie sans IA, en
comparant les mots. Il est volontairement tolérant (fautes corrigées, abréviations développées,
mise en forme ajoutée) et ne cherche que les écarts importants : un cours très raccourci ou
un cours qui contient beaucoup de mots absents des notes.
"""

import re
import unicodedata
from difflib import get_close_matches

# Notes « longues » (mots distincts de 3 lettres ou plus) : contrôle complet.
MIN_WORDS = 30
# En dessous de MIN_WORDS, contrôle plus simple (seulement les mots perdus) ; en dessous de
# MIN_WORDS_SHORT, il n'y a rien à comparer (« f(x)=ax+b »).
MIN_WORDS_SHORT = 4
MAX_MISSING_SHORT = 0.5
# Part maximale des mots des notes qui ne se retrouvent pas dans le cours.
MAX_MISSING = 0.3
# Part maximale des mots du cours qui ne viennent pas des notes.
MAX_ADDED = 0.4

_SPOT = re.compile(r"\[\?([^\]\n|]*)[^\]\n]*\]")  # « [?lecture|autre] » : on garde la lecture
_UNREADABLE = re.compile(r"\[illisible\]", re.IGNORECASE)
_IMAGE = re.compile(r"!\[[^\]\n]*\]\([^)\s]*\)")
_BOX = re.compile(r"^:::\s*(?:definition|propriete|exemple|methode|attention|retenir)\b", re.M)
_LATEX_COMMAND = re.compile(r"\\[A-Za-z]+")
_WORD = re.compile(r"[a-z]{3,}|\d+")


def _words(text: str) -> set[str]:
    plain = unicodedata.normalize("NFD", text.lower())
    plain = "".join(c for c in plain if not unicodedata.combining(c))
    return set(_WORD.findall(plain))


def _found(word: str, pool: set[str]) -> bool:
    """Le mot est dans `pool`, ou y a un proche (abréviation, pluriel, faute de frappe)."""
    if word in pool:
        return True
    if word.isdigit():
        return False
    if any(other.startswith(word) or word.startswith(other) for other in pool):
        return True
    return bool(get_close_matches(word, pool, n=1, cutoff=0.8))


def _share_absent(words: set[str], pool: set[str]) -> float:
    return sum(not _found(word, pool) for word in words) / len(words) if words else 0.0


def keeps_notes(notes: str, course: str) -> bool:
    """Le cours garde l'essentiel des notes et n'y ajoute pas de contenu étranger."""
    clean_notes = _IMAGE.sub(" ", _UNREADABLE.sub(" ", _SPOT.sub(r"\1", notes)))
    clean_course = _LATEX_COMMAND.sub(" ", _BOX.sub(" ", _IMAGE.sub(" ", course)))
    notes_words = _words(clean_notes)
    if len(notes_words) < MIN_WORDS_SHORT:
        return True
    course_words = _words(clean_course)
    if len(notes_words) < MIN_WORDS:
        return _share_absent(notes_words, course_words) <= MAX_MISSING_SHORT
    return (
        _share_absent(notes_words, course_words) <= MAX_MISSING
        and _share_absent(course_words, notes_words) <= MAX_ADDED
    )
