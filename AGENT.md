# AGENT.md

## Projet

NoteClaire est une application web de remise au propre de notes de cours pour des lycéens (seconde, première, terminale). Plusieurs enfants peuvent partager une installation.

Le principe fondamental est de préserver les notes originales de l'élève.
L'IA peut structurer, corriger et proposer des compléments, mais ne doit jamais
ajouter silencieusement du contenu pédagogique.

Le cahier des charges complet est dans `docs/SPEC.md`.

## Stack

Backend:
- Python 3.12+
- FastAPI
- Pydantic
- SQLAlchemy ou SQLModel
- Alembic
- SQLite

Frontend:
- Vue 3
- TypeScript
- Vite
- markdown-it
- KaTeX
- TipTap plus tard, seulement si l'édition Markdown ne suffit pas

Déploiement:
- Docker Compose
- données persistantes dans `/data`

## Architecture

Découpler obligatoirement :
- logique métier
- fournisseur IA
- stockage

Ne jamais appeler directement OpenAI depuis le frontend.

Les providers doivent être interchangeables.

Exemples :
- OpenAIProvider
- LocalProvider (Ollama, LM Studio…)

## Données

Toujours conserver séparément :
1. les notes originales
2. le cours restructuré
3. les suggestions IA

Ne jamais écraser les notes originales.

Le cours est versionné : chaque modification crée une nouvelle version,
aucune version n'est modifiée ni supprimée (voir SPEC §9.1).

Une suggestion acceptée ne s'applique que sur action explicite de l'utilisateur
et seulement si son passage est retrouvé sans ambiguïté (voir SPEC §18.1).

Toute suggestion IA doit conserver :
- texte original
- proposition
- raison
- niveau de confiance
- décision utilisateur

## IA

Ne jamais ajouter silencieusement une information absente des notes.

La mise au propre ne fait que l'orthographe, la ponctuation et la mise en forme :
pas de reformulation, pas de correction de fond.
Ses modifications restent visibles par une comparaison déterministe avec les notes (SPEC §13.1).

Les compléments pédagogiques doivent apparaître comme des suggestions.

Si une information est incertaine, le signaler au lieu de l'inventer.

Les réponses structurées de l'IA doivent être validées avec Pydantic,
en utilisant les structured outputs de l'API OpenAI pour contraindre le format.

Chaque appel IA est journalisé dans `AIRun` (sans le contenu complet du cours).

Le modèle IA doit être configurable par variable d'environnement.

## Élèves

Un chapitre appartient à un élève (`Chapter.student_id`) ; ses matières sont communes.
Toute liste de chapitres, la recherche, la corbeille et les compteurs par matière doivent être
filtrés par l'élève courant (dépendance `StudentDep`, en-tête `X-Student-Id` ou cookie
`noteclaire_student`). Toute route dont l'adresse contient `chapter_id` ou `suggestion_id` est
contrôlée par `require_owner` (404 si le chapitre est à un autre élève) : n'y contournez rien.
La classe de l'élève (`app/levels.py`) alimente les prompts (`{{ level }}`, jamais « seconde »
écrit en dur) et choisit les références (`data/references/<classe>/<matière>/`).
Ajouter une classe = une ligne dans `LEVELS` + ses documents de référence.
Ce n'est pas de la sécurité : pas de compte par élève.

## Programmes de référence

Aucun document officiel dans le dépôt : `backend/app/data/references_catalog.json` liste les
adresses, `services/reference_catalog.py` les télécharge à la demande (jamais en silence) dans
`data/references/<classe>/<matière>/`. Toute nouvelle entrée du catalogue doit être vérifiée
(le lien répond et renvoie un PDF) avant d'être ajoutée.

## Matières

Le catalogue des matières est en base et commun à tous les élèves ; `app/subjects.py` ne sert
qu'à le créer au premier démarrage et à définir les matières habituelles de chaque classe.
Chaque élève a sa sélection (`student_subjects`) : tout menu ou formulaire de chapitre ne doit
proposer que ses matières (`GET /api/subjects`, sans `include_all`). Le `slug` (dossier des références) ne change jamais au renommage.
Une matière n'est supprimable que sans chapitre ni document ; sinon on la désactive.

## Qualité des consignes à l'IA

Les consignes (`backend/app/prompts/*.md`) se jugent avec la vraie IA, pas avec les tests
(qui utilisent une fausse IA). Méthode : un chapitre d'essai avec des notes d'élève réalistes
(fautes, abréviations) contenant **une erreur volontaire**, pour une classe et des
particularités données ; on lance mise au propre, relecture, fiche, quiz et « je n'ai pas
compris », puis on vérifie :
- la mise au propre garde l'erreur (jamais de correction silencieuse) et le vocabulaire de l'élève ;
- la relecture signale l'erreur en premier, avec peu de suggestions, courtes, une confiance
  calibrée, et une source pour tout complément ;
- la fiche et le quiz ne reprennent que le cours, sans section de suggestions ;
- les explications sont courtes, au tutoiement, adaptées aux particularités.
Chaque modification d'une consigne incrémente sa version dans `prompts/__init__.py`.

## Configuration de l'IA

L'assistant de premier lancement écrit `data/secrets/ai.enc` (chiffré), appliqué au démarrage par-dessus
les variables d'environnement (`services/ai_config.py`). La clé API ne doit jamais être renvoyée
au navigateur ni apparaître dans un message d'erreur.

## Connexion ChatGPT

L'adresse de retour OAuth est toujours `http://127.0.0.1:<CHATGPT_REDIRECT_PORT>/auth/callback` :
OpenAI n'accepte que la boucle locale (pas `localhost`, pas un nom de domaine). La connexion se
fait donc depuis la machine hôte ; l'interface désactive le bouton ailleurs
(`frontend/src/lib/chatgptHost.ts`). Libellé du bouton : « Continue with ChatGPT », avec « Using
ChatGPT plan » et le lien « Manage usage » une fois connecté (directives OpenAI).

## Sécurité

Ne jamais exposer les clés API au frontend.

Si `APP_PASSWORD` est défini, toutes les routes API sauf `/api/health` sont protégées (SPEC §27.1).

Ne jamais logger :
- clés API
- secrets
- contenu complet des cours par défaut


## Qualité

Backend :
- pytest
- ruff (dont la complexité des fonctions)
- mypy en mode strict

Frontend :
- eslint
- prettier
- TypeScript (vue-tsc)
- Vitest
- Playwright (`npm run e2e` sur l'application lancée), dont le contrôle d'accessibilité axe

Commandes : `make check` (lint + tests), `make coverage` (couverture, indicative), `make unused`
(code mort et dépendances inutiles ; côté serveur, les champs Pydantic et de dataclasses ne sont pas
signalés, côté interface le bruit connu est `public/sw.js`). Une dépendance importée directement par le code doit être
déclarée dans `package.json` / `pyproject.toml`.

Les tests ne doivent jamais effectuer de véritables appels OpenAI.

## Développement

Avant une modification importante :
1. inspecter le repository
2. comprendre l'architecture existante
3. modifier le minimum nécessaire
4. ajouter ou adapter les tests
5. lancer les tests
6. lancer les linters
7. corriger les erreurs

## Accessibilité : interface adaptée aux enfants dys

NoteClaire est utilisé par des enfants dyslexiques, dyspraxiques, TDAH… L'interface doit leur être
confortable par défaut, pas seulement en option :

- Texte : police Lexend, jamais sous 0,95 rem, ni justifié, ni en majuscules forcées, ni en
  italique ; titres sans interlettrage négatif ; lignes de texte courtes (~70 caractères).
- Cibles : boutons et lignes de cases à cocher d'au moins 44 px, cases 1,5 rem, aucun geste de
  précision (pas de glisser-déposer obligatoire).
- Contrastes suffisants dans chaque thème (clair, crème, sombre) ; l'information n'est jamais
  portée par la couleur seule.
- Réglages d'affichage (Réglages → Affichage) : thème, taille du texte, espacement des lettres.
- Phrases simples, vocabulaire courant, peu de texte à lire d'un coup ; une action principale
  par écran, le reste replié.
- Une nouvelle page est vérifiée par `e2e/accessibility.spec.ts` (axe) : ajouter son adresse
  à la liste des pages contrôlées.

## Schémas redessinés

L'IA ne produit jamais de SVG : elle décrit une scène (inventaire, textes, flèches avec
`head_start`/`head_end`, traits) et `schema_drawing.py` construit le SVG (tracés limités à une liste
de commandes, nombre d'éléments borné, textes échappés). Le SVG est servi avec
`Content-Security-Policy: sandbox` et `nosniff`, la scène est gardée à côté (`.json`) pour les
corrections, et sert aussi à passer à l'aspect manuscrit (`restyle`, sans nouvel appel à l'IA ;
police Caveat, licence OFL, dans `backend/app/assets/`). Pour réviser (fiche, quiz, explications), `describe_schemas` remplace chaque schéma redessiné par
sa description textuelle : l'IA ne voit pas les images. Le schéma d'origine n'est jamais modifié :
le remplacement se fait seulement après accord de l'élève.

## Impression (cours et fiche)

Le PDF vient de « Imprimer » du navigateur (vue `/chapitres/{id}/imprimer`, ou Ctrl+P sur
l'écran du chapitre). Règles : **couleurs oui, aplats de fond non** (économie d'encre : bordures,
libellés, titres et soulignements colorés ; encadrés, tableaux, surlignage et en-tête sans fond ;
schémas à nœuds blancs), **marges de 2,2 cm**, pas de numérotation automatique des titres (le
cours a la sienne), thème clair forcé, aucun bouton ni message à l'impression. Vérifier par un
vrai PDF (Playwright `page.pdf`), pas seulement à l'écran.

## KISS : code simple, maintenable par un humain

Le code doit pouvoir être relu et modifié par une personne qui découvre le projet.

- La solution la plus simple qui répond au besoin. Pas de fonctionnalité « au cas où », pas de
  paramètre ou d'option sans usage actuel, pas de code mort (le supprimer, git s'en souvient).
- Pas de couche d'abstraction (classe, interface, composable, helper) pour un seul usage.
  On factorise à partir de trois répétitions, pas avant ; deux copies courtes valent mieux
  qu'une abstraction obscure.
- Fonctions courtes, qui font une chose. Au-delà de ~50 lignes ou d'une complexité de 11
  (limite vérifiée par ruff), on découpe ou on simplifie.
- Noms explicites en français pour le métier, en anglais pour le code, sans abréviation
  cryptique. Deux champs ne portent jamais des noms presque identiques pour des choses
  différentes.
- Les commentaires expliquent le pourquoi (contrainte, choix non évident), jamais le quoi.
- Une migration Alembic déjà publiée ne se modifie jamais : on en ajoute une nouvelle.
- Préférer les dépendances déjà présentes à une nouvelle bibliothèque.
- Un changement = le minimum de fichiers touchés, avec son test.
