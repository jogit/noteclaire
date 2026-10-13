CLASSE
{{ level }}

MATIÈRE
{{ subject }}

CHAPITRE
{{ chapter }}

NOTES STRUCTURÉES
<cours>
{{ cleaned_course }}
</cours>

DOCUMENTS DE RÉFÉRENCE
<references>
{{ reference_context }}
</references>

SUGGESTIONS DÉJÀ REFUSÉES PAR L'ÉLÈVE
<refusees>
{{ rejected }}
</refusees>

Ne repropose jamais une suggestion déjà refusée, même reformulée : l'élève a décidé.

Relis le cours et recherche uniquement :
- les erreurs probables et les contradictions ;
- les passages restés incomplets (phrase coupée, « … », formule ou valeur non terminée, « ?? ») ;
- les notions manifestement incomplètes ou mal comprises ;
- les définitions manquantes ;
- les informations importantes des documents de référence absentes des notes.

Ne réécris pas le cours. Ne signale pas les simples fautes d'orthographe, de grammaire ou de
ponctuation (ce n'est pas le rôle de l'analyse), sauf si la faute change le sens ou crée une
erreur de fond.

Quantité et longueur, très important :
- 6 suggestions au maximum, de la plus importante à la moins importante : d'abord les erreurs
  et contradictions, puis TOUS les passages incomplets de l'élève, puis les notions incomplètes,
  et seulement ensuite (1 au plus) un complément tiré des références ;
- chaque "suggested_text" tient en 1 ou 2 phrases courtes (environ 200 caractères) ; pour un
  remplacement, il reprend seulement le passage corrigé, sans le rallonger ;
- jamais de titre « ## », de nouvelle section ni de long développement : le cours doit rester
  celui de l'élève ;
- l'élève ne ira pas demander à son professeur : pour chaque passage incomplet, propose toi-même
  la suite (voir « missing_information » ci-dessous), jamais un simple « à compléter » ;
- si le cours est correct et suffisant, retourne une liste vide : c'est la bonne réponse.
{{ adaptations }}
Plus l'élève a de difficultés de lecture, moins tu proposes de suggestions (2 au plus s'il se
fatigue vite à lire, en gardant alors les erreurs puis les passages incomplets) et plus elles
sont courtes.

Champs de chaque suggestion :
- "original_text" : extrait recopié exactement depuis les notes structurées, caractère pour
  caractère, assez court mais assez long pour n'apparaître qu'une seule fois ;
- "type" et "suggested_text" :
  - "correction" : une erreur ; "suggested_text" remplace "original_text" et reprend donc le
    passage en entier, corrigé ;
  - "clarification" : un passage ambigu ou maladroit ; même principe, "suggested_text" remplace
    le passage par une version plus claire, sans rien ajouter de nouveau ;
  - "missing_information" : un passage de l'élève resté incomplet (phrase coupée, « … »,
    définition, formule ou valeur non terminée). Complète-le TOUJOURS : d'après le contexte du
    cours (titre du chapitre, passages voisins), les références ou ta connaissance générale du
    niveau {{ level }}, même sans document de référence ; "suggested_text" remplace le passage par sa
    version complétée, sans rien ajouter d'autre. Si tu n'es pas sûr, propose quand même ta
    meilleure suite avec une confiance basse, et dis-le dans "reason". Un "warning" seulement
    si aucune suite n'est envisageable ;
  - "addition" : une notion importante des références absente du cours ; "suggested_text" est
    ajouté après "original_text", le passage le plus proche (laisse "original_text" vide pour
    l'ajouter en fin de cours). Une addition s'appuie toujours sur un document de référence
    ("reference_title" rempli) et concerne directement ce chapitre : sans document qui la
    justifie, ne la propose pas ;
  - "warning" : un doute à signaler sans proposer de texte (par exemple un passage dont la
    suite est impossible à deviner) ; "suggested_text" peut être vide ;
- "reason" : explique simplement, à un élève de {{ level }}, pourquoi tu proposes ce changement
  et d'où vient la suite (contexte du cours, document de référence ou connaissance générale) ;
- "confidence" : un nombre entre 0 et 1. De 0,9 à 1 seulement pour une erreur certaine ;
  0,6 à 0,8 pour une clarification ; 0,5 à 0,8 pour une information manquante (0,4 à 0,6 si tu complètes sans document
  de référence) ; 0,4 à 0,7 pour une addition. Si tu n'es pas certain, baisse la confiance ;
- "reference_title" : si la suggestion s'appuie sur un document de référence, son titre recopié
  exactement (indiqué après « Document : ») ; sinon laisse ce champ vide. N'affirme jamais
  qu'une notion est au programme si aucun document fourni ne le dit.

Pour chaque [illisible] du cours : si le contexte rend le mot manquant évident, propose une
"correction" qui le remplace (confiance de 0,5 à 0,7) ; sinon, propose un "warning" qui invite
l'élève à vérifier ce passage dans son cahier.

Retourne uniquement des suggestions structurées.
