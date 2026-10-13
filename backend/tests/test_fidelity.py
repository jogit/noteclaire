from app.services.fidelity import keeps_notes

NOTES = """les vecteurs
un vecteur a une direction un sens et une norme
deux vecteurs sont egaux sils ont meme direction meme sens et meme norme
la somme de deux vecteurs u et v se note u+v
relation de chasles AB + BC = AC
le vecteur nul a une norme nulle
coordonnees dun vecteur dans un repere orthonormal
attention a ne pas confondre point et vecteur
ex: A(1;2) et B(4;6) donc AB(3;4) et norme = 5
"""

COURSE = """# Les vecteurs

Un vecteur a une direction, un sens et une norme.

::: definition Égalité de deux vecteurs
Deux vecteurs sont égaux s'ils ont même direction, même sens et même norme.
:::

La somme de deux vecteurs $u$ et $v$ se note $u + v$.

::: propriete Relation de Chasles
$\\overrightarrow{AB} + \\overrightarrow{BC} = \\overrightarrow{AC}$
:::

Le vecteur nul a une norme nulle.

## Coordonnées

Coordonnées d'un vecteur dans un repère orthonormal.

::: attention
Ne pas confondre point et vecteur.
:::

::: exemple
$A(1;2)$ et $B(4;6)$ donc $AB(3;4)$ et norme $= 5$.
:::
"""


def test_formatting_and_spelling_fixes_are_accepted() -> None:
    assert keeps_notes(NOTES, COURSE)


def test_a_summary_is_refused() -> None:
    summary = "# Les vecteurs\n\nUn vecteur a une direction, un sens et une norme.\n"
    assert not keeps_notes(NOTES, summary)


def test_invented_content_is_refused() -> None:
    invented = (
        COURSE
        + "\nLes vecteurs servent aussi en physique pour représenter les forces, les vitesses"
        " et les accélérations. Isaac Newton les utilise dans ses lois du mouvement et leur"
        " étude permet de prévoir les trajectoires des planètes autour du soleil.\n"
    )
    assert not keeps_notes(NOTES, invented)


def test_notes_without_words_are_not_judged() -> None:
    assert keeps_notes("f(x)=ax+b", "# Tout autre texte sans rapport")


def test_short_notes_must_survive() -> None:
    notes = "la somme de deux vecteurs se note u+v, le vecteur nul a une norme nulle"
    assert keeps_notes(notes, "# Vecteurs\n\nLa somme de deux vecteurs se note $u+v$.\n")
    assert not keeps_notes(notes, "# Autre sujet\n\nLa photosynthèse produit du glucose.\n")


def test_uncertain_spots_and_images_do_not_count() -> None:
    notes = NOTES + "\nla [?norme|forme] se mesure\n[illisible]\n![schéma](/api/images/abc123)\n"
    course = COURSE + "\nLa norme se mesure.\n\n![schéma](/api/images/abc123)\n"
    assert keeps_notes(notes, course)
