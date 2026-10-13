Voici le schéma manuscrit d'un élève (image de {{ width }} px de large sur {{ height }} px de haut).

Décris-le élément par élément pour qu'il soit redessiné PROPREMENT, à l'identique : mêmes
éléments, même disposition, mêmes textes, mêmes flèches, aux mêmes positions relatives.
Toutes les coordonnées sont en pixels de cette image : x de 0 (gauche) à {{ width }}, y de 0 (haut)
à {{ height }}.

1. "inventory" : regarde l'image et note UNE ligne par flèche : d'où elle part, où elle arrive,
   y a-t-il une pointe au début ? une pointe à la fin ? (Une flèche peut avoir une pointe aux deux
   bouts. Regarde chaque extrémité l'une après l'autre.)
2. "texts" : tous les textes écrits par l'élève, recopiés fidèlement (voir « corrections » pour les erreurs manifestes).
   Indice : « _{2} » (H_{2}O) ; exposant : « ^{2} » (x^{2}). Un mot vraiment illisible,
   même avec le contexte, s'écrit « [illisible] ». Hauteur des lettres : au moins 22 px.
   Symbole qui existe comme caractère (⇌ → ↔ ≈ ≠ ≤ ± √ ° π…) : écris-le comme texte (centré, taille
   normale), ne le dessine pas avec des traits.
3. "arrows" : une entrée par flèche de l'inventaire (sans les symboles déjà écrits dans "texts"), avec son tracé
   (courbe ou droite, du début vers la fin) et deux réponses : head_start et head_end, identiques à l'inventaire.
4. "lines" : les autres traits (accolades, soulignements, cadres, dessins) sans pointe de flèche.

5. "corrections" : tu relis le schéma comme un professeur. S'il contient une ERREUR MANIFESTE
   (symbole, formule, légende, sens d'une flèche, unité, mot, étiquette…), dessine la version
   CORRECTE et ajoute une phrase simple pour l'élève : ce qui était écrit, ce que tu as mis, et
   pourquoi. Appuie-toi sur le sujet du cours (notes ci-dessous). Si tu as seulement un doute, ne
   change rien au dessin et écris « À vérifier : … ». N'invente pas d'erreur : si tout est juste,
   laisse la liste vide. Une écriture difficile à lire n'est pas une erreur.

Couleurs : chaque texte, flèche et trait garde la couleur de l'encre de l'élève (« noir », « bleu »,
« vert » ou « rouge » ; « noir » si tu hésites).

Tracés : commandes SVG M, L, H, V, C, S, Q, T, A et Z uniquement, avec des nombres. Le tracé d'une
flèche commence là où l'élève a commencé à l'écrire.

Pour te repérer (écriture difficile à lire), voici les notes de l'élève, qui contiennent les mêmes
mots :

<notes>
{{ context }}
</notes>

{{ correction }}