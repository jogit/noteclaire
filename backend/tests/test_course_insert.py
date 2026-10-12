from app.services.course_insert import insert_addition


def add_after(content: str, passage: str, addition: str) -> str:
    return insert_addition(content, content.index(passage) + len(passage), addition)


def test_paragraph_on_several_lines_is_not_split() -> None:
    content = "# T\n\nLa lumière se propage\nen ligne droite.\n\nSuite."
    assert add_after(content, "se propage", "Complément.") == (
        "# T\n\nLa lumière se propage\nen ligne droite.\n\nComplément.\n\nSuite."
    )


def test_table_stays_whole() -> None:
    content = (
        "Avant.\n\n| Élément | Vide |\n| --- | --- |\n| Onde EM | oui |\n| Son | non |\n\nAprès."
    )
    result = add_after(content, "Onde EM", "Le son a besoin d'un milieu.")
    assert result == (
        "Avant.\n\n| Élément | Vide |\n| --- | --- |\n| Onde EM | oui |\n| Son | non |\n\n"
        "Le son a besoin d'un milieu.\n\nAprès."
    )


def test_short_addition_becomes_a_new_list_item() -> None:
    content = "- direction\n- sens\n- norme\n\nFin."
    assert add_after(content, "sens", "même longueur pour des vecteurs égaux") == (
        "- direction\n- sens\n- même longueur pour des vecteurs égaux\n- norme\n\nFin."
    )


def test_numbered_list_keeps_its_numbering() -> None:
    content = "1. Lire l'énoncé\n2. Calculer\n3. Conclure"
    assert add_after(content, "Calculer", "Vérifier l'unité") == (
        "1. Lire l'énoncé\n2. Calculer\n3. Vérifier l'unité\n3. Conclure"
    )


def test_long_addition_goes_after_the_whole_list() -> None:
    content = "- a\n- b\n  suite de b\n- c\n\nFin."
    assert add_after(content, "b", "Premier paragraphe.\n\nSecond.") == (
        "- a\n- b\n  suite de b\n- c\n\nPremier paragraphe.\n\nSecond.\n\nFin."
    )


def test_list_item_with_sub_items() -> None:
    content = "- a\n  - a1\n  - a2\n- b"
    assert add_after(content, "a", "a bis") == "- a\n  - a1\n  - a2\n- a bis\n- b"


def test_math_block_is_not_cut() -> None:
    content = "Formule :\n\n$$\nv = \\frac{d}{t}\n$$\n\nSuite."
    assert add_after(content, "\\frac{d}{t}", "Avec $d$ en mètres.") == (
        "Formule :\n\n$$\nv = \\frac{d}{t}\n$$\n\nAvec $d$ en mètres.\n\nSuite."
    )


def test_callout_keeps_the_addition_inside() -> None:
    content = "::: definition Vecteur\nUn vecteur a une direction.\n:::\n\nSuite."
    assert add_after(content, "une direction", "Il a aussi un sens.") == (
        "::: definition Vecteur\nUn vecteur a une direction.\n\nIl a aussi un sens.\n:::\n\nSuite."
    )
