# Guide d'utilisation

Un chapitre se fait en trois étapes : **Mes notes → Mon cours → Réviser**.

## Mes notes

Les notes sont du texte simple, dans un éditeur qui montre directement le contenu.

- **Photos des notes** : l'IA recopie fidèlement le texte, sans rien corriger.
  - *Plusieurs pages* : choisissez toutes les photos d'un coup, ou ajoutez-les au fur et à mesure
    (même d'une séance à l'autre). Chaque page s'ajoute à la suite des notes, dans l'ordre. Une
    photo illisible n'arrête pas les autres : elle est signalée et peut être réessayée seule.
  - *Mots difficiles* : ils deviennent des étiquettes (jaune : lecture douteuse, orange :
    illisible). Un clic propose 2 ou 3 lectures, ou de taper ce qu'on lit dans le cahier.
    « Vérifier le suivant » passe d'un passage à l'autre, la photo reste affichée à côté.
  - *Schémas* : l'IA les repère sur la photo et les **découpe automatiquement** dans les notes.
    Sous les notes, « Schémas de tes notes » propose de les **redessiner proprement** (mêmes textes
    et mêmes flèches). On compare avec sa photo, on dit ce qui ne va pas (« il manque la pointe de
    la flèche à gauche ») pour que l'IA corrige, et rien ne remplace la photo sans accord.
    « Découper un schéma » insère à la main une partie de la photo.
  - La photo d'origine est conservée avec le chapitre (bouton « Photos d'origine »), sans ses
    métadonnées.
- **Image / schéma** : ajoute une photo de schéma à l'endroit voulu.

La mise au propre demande confirmation s'il reste des passages à vérifier, et garde les images à
leur place dans le cours.

## Mon cours et la relecture

L'écran du cours montre une seule chose à la fois, pour ne pas surcharger un élève dys.

- **Relecture** : après la mise au propre, l'IA relit le cours. Une barre annonce « 3 points à
  regarder » ; « Regarder » les présente **un par un** dans un panneau en bas de l'écran, avec
  seulement le passage concerné surligné. Rien ne change sans « Accepter ».
- **Je n'ai pas compris** : sélectionner un passage ouvre une explication très courte (3 phrases
  au plus). Ensuite : « J'ai compris », ou une autre explication, un exemple, une question. Rien
  n'est ajouté au cours.
- **Modifier** (éditeur visuel ou Markdown), **Ce que l'IA a changé** (comparaison avec les notes)
  et **Versions** sont des boutons au-dessus du cours.

## Réviser et exporter

- **Fiche de révision** et **quiz** (QCM, vrai/faux, réponse courte), générés à partir du cours
  courant uniquement ; signalés comme obsolètes si le cours change ensuite.
- **Export du quiz pour Anki** : un fichier texte à importer dans Anki (Fichier → Importer), une
  carte par question, avec la bonne réponse, l'explication et l'extrait du cours.
- **Export du cours** : Markdown, ou PDF par « Imprimer → Enregistrer au format PDF » du navigateur
  (rendu exact des formules, en-tête et pagination).
- **Recherche** (en-tête) dans les titres, matières, notes et cours, sans tenir compte des accents.

## Plusieurs enfants

Dans Réglages → Élèves, ajoutez un élève par enfant avec sa classe. Un menu « Élève » apparaît dans
la navigation. Chaque élève a ses chapitres, ses matières (préremplies selon sa classe, à cocher
dans sa fiche), sa recherche et sa corbeille ; l'IA adapte ses explications à sa classe et à ses
particularités (dyslexie, dyspraxie, TDAH…, plus un champ libre).

Le serveur refuse l'accès d'un élève aux chapitres d'un autre. Le choix de l'élève est mémorisé par
navigateur, donc chaque enfant peut avoir son appareil. Il n'y a pas de mot de passe par élève :
`APP_PASSWORD` est commun à la famille, et changer d'élève dans le navigateur reste libre.

## Ne rien perdre

- **Historique des notes** (bouton « Historique ») : une copie toutes les 15 minutes de travail,
  après chaque photo importée, avant chaque mise au propre et avant un gros effacement. « Remettre
  cette version » garde les notes actuelles dans l'historique (50 versions par chapitre).
- **Corbeille** : un chapitre supprimé y reste 30 jours, avec ses notes, cours, fiches, images et
  photos.
- **Sauvegardes** : chaque jour, une archive `noteclaire-AAAAMMJJ-HHMMSS.zip` (base, images et photos ;
  jamais les jetons ChatGPT), les 7 dernières sont gardées. « Sauvegarder maintenant » et le
  téléchargement sont dans les Réglages.

**Restaurer** : Réglages → Sauvegardes → « Restaurer » à côté d'une sauvegarde, ou « Restaurer
depuis un fichier » pour reprendre une sauvegarde d'une autre installation. Tout est vérifié avant
de toucher aux données, puis l'état actuel est sauvegardé : une restauration se défait en restaurant
cette copie. Une sauvegarde d'une autre version de NoteClaire est refusée. La connexion ChatGPT n'est
pas sauvegardée : il suffit de se reconnecter dans les Réglages.

## Affichage

Réglages → Affichage : thème (clair, crème, sombre, comme l'appareil), taille du texte (Normal,
Grand, Très grand), espacement des lettres et des mots. Ces choix sont mémorisés par navigateur.
