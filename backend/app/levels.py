"""Classes proposées : (identifiant, libellé affiché, nom utilisé dans les prompts IA).

L'identifiant est aussi le nom du dossier `data/references/<identifiant>/`.
"""

LEVELS: list[tuple[str, str, str]] = [
    ("seconde", "Seconde", "seconde"),
    ("premiere", "Première générale", "première générale"),
    ("terminale", "Terminale générale", "terminale générale"),
    ("premiere-techno", "Première technologique", "première technologique"),
    ("terminale-techno", "Terminale technologique", "terminale technologique"),
]
DEFAULT_LEVEL = "seconde"
LEVEL_IDS = [level_id for level_id, _, _ in LEVELS]


def prompt_label(level: str) -> str:
    """Nom de la classe dans les prompts (« première » plutôt que « premiere »)."""
    return next((label for level_id, _, label in LEVELS if level_id == level), level)


# Particularités proposées : (identifiant, libellé affiché, formulation donnée à l'IA).
ADAPTATIONS: list[tuple[str, str, str]] = [
    ("dyslexie", "Dyslexie", "dyslexique (phrases courtes, mots simples, texte aéré)"),
    ("dysorthographie", "Dysorthographie", "dysorthographique (ne pas relever ses fautes)"),
    ("dysgraphie", "Dysgraphie", "dysgraphique (écriture difficile à lire)"),
    ("dyspraxie", "Dyspraxie", "dyspraxique (schémas et cartes mentales simples)"),
    ("dyscalculie", "Dyscalculie", "dyscalculique (calculs expliqués pas à pas)"),
    ("tdah", "TDAH", "avec un trouble de l'attention (une seule idée à la fois)"),
    (
        "haut-potentiel",
        "Haut potentiel",
        "à haut potentiel (peut aller plus vite, aime comprendre pourquoi)",
    ),
    (
        "fatigue-lecture",
        "Se fatigue vite à lire",
        "qui se fatigue vite à lire (aller à l'essentiel)",
    ),
]
ADAPTATION_IDS = [adaptation_id for adaptation_id, _, _ in ADAPTATIONS]


def adaptations_text(codes: str, free_text: str = "") -> str:
    """Phrase ajoutée aux prompts (vide si l'élève n'a aucune particularité renseignée).

    `codes` : identifiants séparés par des virgules, tels que stockés.
    """
    wanted = {code for code in codes.split(",") if code}
    parts = [phrase for adaptation_id, _, phrase in ADAPTATIONS if adaptation_id in wanted]
    if free_text.strip():
        parts.append(free_text.strip())
    return f"Particularités de l'élève, à respecter : {' ; '.join(parts)}." if parts else ""
