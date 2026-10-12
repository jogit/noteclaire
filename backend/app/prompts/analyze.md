MATIÈRE
{{ subject }}

CHAPITRE
{{ chapter }}

NOTES STRUCTURÉES
{{ cleaned_course }}

DOCUMENTS DE RÉFÉRENCE
{{ reference_context }}

SUGGESTIONS DÉJÀ REFUSÉES PAR L'ÉLÈVE
{{ rejected }}

Ne repropose jamais une suggestion déjà refusée, même reformulée : l'élève a décidé.

Recherche uniquement :
- erreurs probables ;
- contradictions ;
- notion manifestement incomplète ;
- définition manquante ;
- élément du cours qui semble mal compris ;
- information importante présente dans les références mais absente des notes.

Ne réécris pas le cours.

Quantité et longueur, très important :
- 4 suggestions au maximum, de la plus importante à la moins importante : d'abord les erreurs
  et contradictions, puis les notions incomplètes, et seulement ensuite (2 au plus) des
  compléments tirés des références ;
- chaque "suggested_text" tient en 1 ou 2 phrases courtes (environ 200 caractères) ; pour une
  "correction", il reprend seulement le passage corrigé, sans le rallonger ;
- jamais de titre « ## », de nouvelle section ni de long développement : le cours doit rester
  celui de l'élève ;
- une "addition" s'appuie toujours sur un document de référence ("reference_title" rempli) ;
  sans document qui la justifie, ne la propose pas ;
- si le cours est correct et suffisant, ne propose rien d'optionnel : une liste vide est la
  bonne réponse.
{{ adaptations }}
Plus l'élève a de difficultés de lecture, moins tu proposes de suggestions (2 au plus s'il se
fatigue vite à lire) et plus elles sont courtes.

Retourne uniquement des suggestions structurées.

Pour chaque suggestion, "original_text" doit être recopié exactement
depuis les notes structurées, caractère pour caractère. Choisis un extrait
court mais assez long pour n'apparaître qu'une seule fois.

Selon le type :
- "correction", "clarification", "missing_information" : "suggested_text"
  remplace "original_text" dans le cours ; il reprend donc le passage en entier,
  corrigé ou complété ;
- "addition" : "suggested_text" est un complément ajouté après "original_text"
  (laisse "original_text" vide pour l'ajouter en fin de cours) ;
- "warning" : signale un doute sans proposer de texte ; "suggested_text" peut être vide.

"reason" explique simplement, à un élève de {{ level }}, pourquoi tu proposes ce changement.
"confidence" est un nombre entre 0 et 1 : 0,9 à 1 seulement pour une erreur certaine ;
0,6 à 0,8 pour une clarification ; 0,4 à 0,7 pour un complément.

"reference_title" : si la suggestion s'appuie sur un document de référence, recopie
exactement son titre (indiqué après "Document :"). Sinon, laisse ce champ vide.
N'affirme jamais qu'une notion est au programme si aucun document fourni ne le dit.

Quand une information importante des documents de référence manque dans le cours,
propose-la en "addition", placée après le passage du cours le plus proche.
Ne propose que ce qui concerne directement ce chapitre.

Pour chaque [illisible] du cours : si le contexte rend le mot manquant évident, propose une
"correction" qui le remplace (confiance modérée) ; sinon, propose un "warning" qui invite
l'élève à vérifier ce passage dans son cahier.

Si tu n'es pas certain, diminue le niveau de confiance.
Si le cours ne pose aucun problème, retourne une liste vide.
