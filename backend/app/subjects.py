"""Matières créées au premier démarrage. Ensuite elles se gèrent dans les Réglages (§8)."""

SUBJECTS: list[tuple[str, str]] = [
    ("francais", "Français"),
    ("mathematiques", "Mathématiques"),
    ("histoire-geographie", "Histoire-Géographie"),
    ("ses", "SES"),
    ("physique-chimie", "Physique-Chimie"),
    ("svt", "SVT"),
    ("anglais", "Anglais"),
    ("espagnol", "Espagnol"),
    ("allemand", "Allemand"),
    ("snt", "SNT"),
    ("emc", "EMC"),
    ("philosophie", "Philosophie"),
    ("enseignement-scientifique", "Enseignement scientifique"),
    ("nsi", "NSI"),
    ("hggsp", "HGGSP"),
    # Options de seconde et spécialités techniques, sous le nom que les élèves leur donnent.
    ("sciences-ingenieur", "Sciences de l'ingénieur"),
    ("cit", "Création et innovation technologiques"),
    ("management-gestion", "Management et gestion"),
    ("biotechnologies", "Biotechnologies"),
    ("creation-culture-design", "Création et culture-design"),
    ("danse-musique-theatre", "Danse, musique ou théâtre"),
    # Séries technologiques : une matière par série, qui regroupe ses enseignements.
    ("stmg", "STMG"),
    ("sti2d", "STI2D"),
    ("stl", "STL"),
    ("st2s", "ST2S"),
    ("std2a", "STD2A"),
    ("s2tmd", "S2TMD"),
    ("sthr", "STHR"),
]

# Matières activées au départ pour un élève, selon sa classe (modifiable ensuite dans les Réglages).
_COMMON = ["histoire-geographie", "anglais", "espagnol", "allemand", "emc"]
_SPECIALITES = ["mathematiques", "physique-chimie", "svt", "ses", "nsi", "hggsp"]
DEFAULTS_BY_LEVEL: dict[str, set[str]] = {
    "seconde": {
        *_COMMON,
        "francais",
        "mathematiques",
        "ses",
        "physique-chimie",
        "svt",
        "snt",
    },
    "premiere": {*_COMMON, "francais", "enseignement-scientifique", *_SPECIALITES},
    "terminale": {*_COMMON, "philosophie", "enseignement-scientifique", *_SPECIALITES},
    # Tronc commun technologique : on coche ensuite la série (STMG, STI2D…).
    "premiere-techno": {*_COMMON, "francais", "mathematiques"},
    "terminale-techno": {*_COMMON, "philosophie", "mathematiques"},
}
