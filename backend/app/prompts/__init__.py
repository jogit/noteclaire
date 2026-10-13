import hashlib
import re
from functools import cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent

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


@cache
def prompt_version(name: str) -> str:
    """Empreinte du prompt (et du prompt système) : change d'elle-même dès qu'un texte change.

    Sert à l'audit des appels IA (`AIRun.prompt_version`), sans numéro à incrémenter à la main.
    """
    text = load_prompt("system") + load_prompt(name)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:10]
