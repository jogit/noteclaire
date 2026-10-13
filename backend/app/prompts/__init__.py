import re
from functools import cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent

# À incrémenter à chaque modification d'un prompt (sert à l'audit et au futur cache).
STRUCTURE_PROMPT_VERSION = "structure-v9"
ANALYZE_PROMPT_VERSION = "analyze-v6"
REVISION_SHEET_PROMPT_VERSION = "revision-sheet-v12"
QUIZ_PROMPT_VERSION = "quiz-v3"
EXPLAIN_PROMPT_VERSION = "explain-v4"
PHOTO_PROMPT_VERSION = "photo-v5"
FIGURES_PROMPT_VERSION = "figures-v1"
REDRAW_PROMPT_VERSION = "redraw-v7"


_VARIABLE = re.compile(r"\{\{ (\w+) \}\}")
# Balises qui délimitent les données de l'élève dans les prompts (voir system.md).
_DATA_TAG = re.compile(
    r"<(/?)(notes|cours|passage|references|refusees|remarque|particularites)\s*>", re.I
)
# Valeurs construites par le code lui-même (elles contiennent nos propres balises).
_TRUSTED = frozenset({"correction", "adaptations"})


def escape_data(text: str) -> str:
    """Une donnée ne peut ni fermer ni ouvrir nos balises (« </cours> » devient « &lt;/cours> »)."""
    return _DATA_TAG.sub(lambda found: f"&lt;{found.group(1)}{found.group(2)}>", text)


@cache
def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def render_prompt(name: str, **values: str) -> str:
    """Remplace les variables {{ nom }}. Les valeurs ne sont pas réinterprétées."""
    safe = {k: v if k in _TRUSTED else escape_data(v) for k, v in values.items()}
    return _VARIABLE.sub(lambda found: safe.get(found.group(1), found.group(0)), load_prompt(name))
