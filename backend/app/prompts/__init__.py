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


@cache
def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def render_prompt(name: str, **values: str) -> str:
    """Remplace les variables {{ nom }}. Les valeurs ne sont pas réinterprétées."""
    return _VARIABLE.sub(
        lambda found: values.get(found.group(1), found.group(0)), load_prompt(name)
    )
