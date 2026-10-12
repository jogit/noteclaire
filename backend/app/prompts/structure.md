Classe :
{{ level }}

Matière :
{{ subject }}

Chapitre :
{{ chapter }}

Notes de l'élève :

{{ raw_notes }}

Réorganise uniquement ces notes.

Tu peux :
- corriger l'orthographe ;
- corriger la ponctuation ;
- organiser les paragraphes ;
- créer des titres et sous-titres ;
- transformer certaines parties en listes ;
- écrire les formules en LaTeX ($...$ ou $$...$$) ; les formules chimiques et les unités
  s'écrivent droites : $\mathrm{H_2O}$, $\mathrm{Na^+}$, $5\ \mathrm{cm}$.

Tu ne dois pas :
- reformuler les phrases de l'élève ;
- corriger une erreur de fond, même évidente ;
- ajouter une notion de cours absente ;
- inventer un exemple ;
- inventer une définition ;
- compléter toi-même une information manquante.

Pour que le cours soit clair et agréable à relire, mets en forme le contenu DES NOTES avec :
- des encadrés : une ligne « ::: type Titre facultatif », le contenu, puis une ligne « ::: ».
  Types : definition, propriete (propriété, théorème, formule), exemple, methode,
  attention (piège ou erreur fréquente notés par l'élève), retenir ;
- le surlignage ==mot-clé== pour quelques mots importants (un ou deux par paragraphe au plus) ;
- un tableau Markdown quand les notes comparent plusieurs éléments.
Ces outils ne servent qu'à présenter ce qui est déjà dans les notes : n'ajoute rien.
Garde tels quels les « [schéma : …] » : l'élève y ajoutera la photo du schéma.
Un passage noté « [?lecture|autre lecture] » est une lecture incertaine d'une photo :
écris la première lecture telle quelle. Un « [illisible] » reste « [illisible] ».
Garde aussi, à leur place, les images des notes (lignes « ![légende](/api/images/…) »),
sans changer leur adresse.

Les notes peuvent venir de plusieurs pages ou de plusieurs séances, mises bout à bout : garde
tout le contenu, dans l'ordre. Les numéros de page, dates de séance et mentions du type
« page 2 » ou « suite » ne font pas partie du cours : ne les garde pas dans les titres ni dans
le texte.

Commence le cours par un titre de niveau 1 (« # … ») : un titre clair et court pour le
chapitre, déduit des notes, sans faute, sans numéro de chapitre et sans [illisible]
(exemple : « # Les vecteurs »).

Si un passage est illisible ou incompréhensible, conserve-le tel quel
(un [illisible] reste [illisible] : ne devine pas).
Les erreurs de fond seront traitées séparément par l'analyse.

Retourne le résultat au format demandé : le cours en Markdown dans "clean_course".


{{ adaptations }}
S'il y a des particularités ci-dessus, elles ne changent que la PRÉSENTATION (paragraphes courts,
listes, texte aéré) : n'enlève, n'ajoute et ne simplifie aucun contenu.
