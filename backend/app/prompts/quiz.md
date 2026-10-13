CLASSE
{{ level }}

MATIÈRE
{{ subject }}

CHAPITRE
{{ chapter }}

COURS VALIDÉ PAR L'ÉLÈVE
<cours>
{{ course }}
</cours>

Crée un quiz pour réviser ce cours, uniquement à partir de son contenu : 6 à 10 questions,
moins si le cours est court (jamais de question en double ni de question sans intérêt pour
atteindre un nombre). Suis l'ordre du cours.

Règles :
- chaque question porte sur une information présente dans le cours, et n'invente aucune notion
  absente du cours ;
- ne pose aucune question sur un passage douteux ([illisible], « ?? », « à vérifier », phrase
  ou formule restée incomplète) ;
- varie les types :
  - "qcm" : 3 ou 4 propositions dans "choices", une seule juste, recopiée à l'identique
    dans "answer" ; les mauvaises propositions sont plausibles, de longueur comparable, et la
    bonne n'est pas toujours à la même place ;
  - "true_false" : "choices" vide, "answer" vaut "Vrai" ou "Faux" ; mélange affirmations
    vraies et fausses (une affirmation fausse est une déformation d'une notion du cours) ;
  - "short" : réponse courte (un mot, un nombre, une formule), "choices" vide ;
- "explanation" : une phrase simple qui explique la bonne réponse ;
- "course_excerpt" : extrait exact du cours (recopié caractère pour caractère) qui
  justifie la réponse ;
- formules en LaTeX ($...$).

{{ adaptations }}
S'il y a des particularités ci-dessus, adapte seulement la formulation des questions (courtes,
claires, une seule idée par question), pas leur niveau ni leur contenu.
