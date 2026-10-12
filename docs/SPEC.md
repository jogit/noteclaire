# SPEC — NoteClaire

## 1. Objectif

Développer une application web permettant à un lycéen de seconde de transformer ses notes manuscrites ou saisies en un cours numérique propre, structuré et exploitable pour les révisions.

Le contexte principal est celui d'un élève dyspraxique qui continue à prendre ses notes à la main en classe.

L'application intervient ensuite, à la maison, afin de :
- retranscrire les notes ;
- les structurer ;
- corriger les erreurs manifestes ;
- détecter les passages incomplets ou douteux ;
- proposer des compléments ;
- s'appuyer sur le programme officiel de seconde ;
- produire une version propre du cours ;
- conserver une distinction claire entre les notes d'origine et les informations ajoutées par l'IA.

Principe fondamental :

> L'IA aide à reconstruire le cours de l'élève. Elle ne doit jamais remplacer silencieusement ses notes par un cours généré.

---

## 2. Utilisateurs

Utilisateur principal :
- lycéen (seconde, première ou terminale) ;
- prise de notes manuscrite conservée en classe ;
- remise au propre à la maison.

Utilisateur secondaire :
- parent aidant à la retranscription et à la validation.

Plusieurs enfants peuvent partager une installation : chacun est un « élève » (§9, Student) avec
sa classe. Il n'y a pas de comptes ni de mots de passe par élève : l'élève courant est choisi
dans le navigateur (en-tête `X-Student-Id` ou cookie `noteclaire_student`, par défaut le premier
élève). Le serveur refuse (404) l'accès à un chapitre, à ses images, photos et suggestions depuis
un autre élève ; en revanche changer d'élève est libre : rien ne l'empêche sans compte par élève.

---

## 3. Workflow principal

1. Sélectionner une matière.
2. Créer ou ouvrir un chapitre.
3. Saisir du texte et/ou photographier ses notes manuscrites.
4. Relire et corriger le texte brut.
5. Corriger manuellement si besoin.
6. Cliquer sur `Mettre le cours au propre`.
7. L'IA structure le texte et corrige uniquement l'orthographe, la ponctuation et la mise en forme.
8. Afficher le cours propre, avec la possibilité de voir les modifications par rapport aux notes (voir §13.1).
9. Lancer l'analyse : l'IA détecte les passages douteux et propose des corrections et compléments.
10. Afficher séparément :
    - le cours propre ;
    - les corrections proposées ;
    - les compléments ;
    - les éléments incertains.
11. Accepter ou refuser chaque suggestion.
12. Chaque modification du cours crée une nouvelle version (voir §9.1).
13. Générer ensuite fiche de révision et quiz.

---

## 4. Philosophie produit

Priorités :
- simplicité ;
- lisibilité ;
- faible charge cognitive ;
- grosses zones cliquables ;
- interface peu chargée ;
- sauvegarde automatique ;
- transparence des modifications IA.

L'utilisateur doit toujours savoir ce qui vient de ses notes et ce qui vient de l'IA.

---

## 5. Architecture

```text
Navigateur
    |
    v
Frontend Vue
    |
    v
API FastAPI
    |
    +---- SQLite
    |
    +---- références pédagogiques
    |
    +---- AI Provider
    |       +---- OpenAI
```

Découpler :
- modèle IA ;
- logique métier ;
- stockage.

Ne jamais appeler OpenAI directement depuis le frontend.

---

## 6. Stack

### Backend
- Python 3.12+
- FastAPI
- Pydantic
- SQLAlchemy ou SQLModel
- Alembic
- SQLite

### Frontend
- Vue 3
- TypeScript
- Vite
- markdown-it
- KaTeX
- TipTap plus tard, seulement si l'édition Markdown ne suffit pas

### Déploiement
- Docker Compose
- volume persistant `/data`

---

## 7. Configuration

Variables d'environnement uniquement.

```env
APP_ENV=production
LOG_LEVEL=INFO
APP_PASSWORD=

DATABASE_URL=sqlite:////data/app.db
DATA_DIR=/data

AI_PROVIDER=openai
OPENAI_API_KEY=
OPENAI_MODEL=gpt-6-luna
AI_TIMEOUT_SECONDS=120

AI_MONTHLY_BUDGET_EUR=5
AI_INPUT_PRICE_EUR_PER_MTOK=
AI_OUTPUT_PRICE_EUR_PER_MTOK=
```

`APP_PASSWORD` : voir §27.

En développement hors Docker, `DATA_DIR` et `DATABASE_URL` pointent vers le dossier local `./data`.

Modèle local (Ollama, LM Studio, llama.cpp… : toute API compatible OpenAI) :

```env
AI_PROVIDER=local
LOCAL_AI_BASE_URL=http://host.docker.internal:11434/v1
LOCAL_AI_MODEL=qwen3:8b
```

Un modèle local est gratuit : il n'est pas soumis au budget IA.

---

## 8. Matières

Au minimum :
- Français
- Mathématiques
- Histoire-Géographie
- SES
- Physique-Chimie
- SVT
- Anglais
- Espagnol
- Allemand
- SNT
- EMC
- Philosophie, Enseignement scientifique, NSI, HGGSP (première et terminale)

Ne pas coder la liste à plusieurs endroits. Cette liste n'est que le point de départ :
les matières se gèrent ensuite dans les Réglages (table `subjects`, ordre `position`) et chaque
élève choisit celles qu'il suit (`student_subjects`).

---

## 9. Modèle de données

### Student
- id
- name
- level (`seconde`, `premiere`, `terminale`, `premiere-techno` ou `terminale-techno`, liste unique
  dans `backend/app/levels.py`)
- adaptation_codes (cases à cocher parmi `levels.ADAPTATIONS` : dyslexie, dyspraxie, TDAH…)
- adaptation_notes (précision libre facultative) ; les deux sont ajoutés aux prompts d'explication
  et de fiche, seulement s'ils sont renseignés
- created_at

La classe de l'élève détermine le niveau annoncé à l'IA dans chaque prompt
(variable `{{ level }}`) et les documents de référence utilisés (§20).
Un élève ne peut être supprimé que s'il n'a aucun chapitre, corbeille comprise,
et il en faut toujours au moins un.

### Subject
- id
- name
- slug
- created_at

### Chapter
- id
- subject_id
- student_id
- title
- description
- school_year
- created_at
- updated_at

### Note
- id
- chapter_id
- raw_text
- source
- created_at
- updated_at

Sources :
- keyboard
- photo
- mixed

### Course
Une ligne par version. Une version n'est jamais modifiée ni supprimée.

- id
- chapter_id
- content_markdown
- version (entier croissant par chapitre)
- origin
- source_notes_hash
- ai_run_id (nullable)
- created_at

Origines :
- ai_structure : produite par `Mettre le cours au propre`
- user_edit : modifiée à la main par l'utilisateur
- suggestion_applied : produite par l'acceptation d'une suggestion

`source_notes_hash` : hash SHA-256 du `raw_text` des notes au moment de la génération.
Le cours courant est la version la plus élevée du chapitre.

### AISuggestion
- id
- chapter_id
- course_version_id (version du cours analysée)
- type
- original_text
- suggested_text
- reason
- confidence (0 à 1)
- status
- ai_run_id
- created_at
- decided_at

Types :
- correction
- missing_information
- clarification
- addition
- warning

Statuts :
- pending
- accepted
- rejected
- outdated (le passage visé n'existe plus dans le cours courant)

### AIRun
Journal de chaque appel IA (audit et coûts).

- id
- chapter_id
- operation (structure, analyze, explain, revision_sheet, quiz)
- provider
- model
- prompt_version
- input_hash
- input_tokens
- output_tokens
- estimated_cost_eur (nullable)
- status (success, error)
- error_code (nullable)
- duration_ms
- created_at

Ne pas y stocker le contenu complet des notes ou du cours : le hash et les références suffisent.

### ReferenceDocument
- id
- subject_id
- title
- source
- school_year
- content
- created_at

### 9.1 Cycle de vie notes → cours

Les notes sont la source. Le cours est dérivé des notes.

Règles :
- les notes restent toujours modifiables, indépendamment du cours ;
- chaque changement du cours (IA, édition manuelle, suggestion acceptée) crée une nouvelle version `Course` ;
- si le hash des notes actuelles diffère du `source_notes_hash` du cours courant, afficher :
  « Tes notes ont changé depuis la dernière mise au propre. » avec le bouton `Remettre au propre` ;
- relancer la mise au propre crée une nouvelle version à partir des notes, sans fusion automatique ;
- si le cours courant contient des modifications manuelles (une version `user_edit` ou `suggestion_applied` depuis la dernière `ai_structure`), demander confirmation :
  « Tes modifications du cours resteront disponibles dans l'historique. » ;
- quand une nouvelle version est créée, les suggestions `pending` dont le passage visé n'existe plus passent à `outdated`.

---

## 10. Écran principal

```text
----------------------------------------------------
Mathématiques > Fonctions affines
----------------------------------------------------

NOTES

[ Grande zone de texte                         ]
[                                              ]
[                                              ]

Sauvegardé automatiquement

[ Mettre le cours au propre ]

COURS PROPRE                  [ Voir les modifications ]

Rendu Markdown + formules
----------------------------------------------------
```

La zone de notes est une simple zone de texte (`textarea`) : les notes sont du texte brut.

Le cours est rendu en lecture avec markdown-it + KaTeX.
L'édition manuelle du cours se fait en Markdown avec aperçu.
TipTap n'est introduit que si cette édition s'avère insuffisante à l'usage.

---

## 11. Dictée vocale

Hors périmètre (voir §36).

---

## 12. Providers

### AIProvider

```python
class AIProvider:
    async def structure_course(...):
        ...

    async def analyze_course(...):
        ...

    async def generate_revision_sheet(...):
        ...

    async def generate_quiz(...):
        ...
```

Implémentations :
- OpenAIProvider (Responses API + structured outputs)
- ChatGPTProvider (abonnement ChatGPT via « Sign in with ChatGPT », même API en flux continu,
  `store: false`, repli sur une consigne JSON si le format imposé n'est pas accepté)
- LocalProvider (Chat Completions + `response_format`, pour Ollama, LM Studio…)

---

## 13. Pipeline IA

### Étape 1 — Nettoyage
Corriger :
- ponctuation ;
- paragraphes ;
- orthographe ;
- erreurs évidentes de transcription.

Ne pas ajouter de connaissances.

### Étape 2 — Structuration
Transformer en Markdown structuré :
- titres ;
- sous-titres ;
- listes ;
- définitions ;
- formules ;
- exemples.

### Étape 3 — Analyse
Comparer le cours avec les références disponibles.

Détecter :
- erreurs probables ;
- incohérences ;
- informations manquantes ;
- notions mentionnées mais non expliquées.

### Étape 4 — Suggestions
Ne pas modifier le cours automatiquement.

Les étapes 1 et 2 forment l'opération `structure` (bouton `Mettre le cours au propre`).
Les étapes 3 et 4 forment l'opération `analyze`, déclenchée séparément.

### 13.1 Transparence de la mise au propre

Même limitées à l'orthographe et à la mise en forme, les modifications de l'étape 1 doivent rester visibles.

Le bouton `Voir les modifications` affiche une comparaison mot à mot entre les notes et le cours propre :
- calculée de façon déterministe (pas par l'IA) ;
- en ignorant la syntaxe Markdown (`#`, `-`, `*`, `$`…) et les espaces / retours à la ligne ;
- mots supprimés barrés, mots ajoutés soulignés, avec une légende textuelle (pas seulement la couleur).

Si une part importante du texte a été ajoutée par rapport aux notes, afficher un avertissement :
« Le cours contient du texte absent de tes notes. Vérifie les passages soulignés. »

---

## 14. Format de réponse IA

JSON structuré, validé par Pydantic.

Utiliser les *structured outputs* de l'API OpenAI (schéma JSON généré depuis les modèles Pydantic) pour contraindre la réponse.
La validation Pydantic côté backend reste obligatoire, quel que soit le provider (Ollama ne garantit pas le schéma).

Réponse de `structure` :

```json
{
  "clean_course": "# Les fonctions affines\n..."
}
```

Réponse de `analyze` :

```json
{
  "suggestions": [
    {
      "type": "correction",
      "original_text": "si a est zéro la fonction monte",
      "suggested_text": "si a = 0, la fonction est constante",
      "reason": "Une fonction affine de coefficient directeur nul est constante.",
      "confidence": 0.98
    }
  ]
}
```

`original_text` doit être un extrait exact du cours analysé (voir §18.1).
Pour un type `addition`, `original_text` est le passage après lequel insérer le complément, ou vide pour l'ajouter en fin de cours.

Les formules sont écrites en LaTeX : `$...$` en ligne, `$$...$$` en bloc.

Si la réponse est invalide :
- une seule nouvelle tentative ;
- sinon erreur explicite et `AIRun` en statut `error` ;
- jamais d'enregistrement partiel silencieux.

---

## 15. Prompt système

```text
Tu es un assistant pédagogique chargé d'aider un lycéen français
à remettre au propre ses propres notes de cours.

Tu ne dois pas remplacer ses notes par un cours entièrement généré.

Priorités :
1. conserver le contenu de l'élève ;
2. améliorer la lisibilité ;
3. structurer le contenu ;
4. détecter les erreurs probables ;
5. détecter les informations importantes qui semblent manquer ;
6. proposer des corrections et compléments séparément.

Tu ne dois jamais ajouter silencieusement une information pédagogique
qui n'était pas dans les notes.

Toute correction ou information supplémentaire doit apparaître dans
la liste des suggestions.

Lorsque tu n'es pas certain, indique une incertitude au lieu d'inventer.

Le niveau scolaire est la classe de seconde du lycée français.

Utilise les documents de référence fournis lorsqu'ils sont disponibles.

Ne prétends jamais qu'une notion figure dans le programme officiel
si cette information n'apparaît pas dans les documents de référence fournis.

Le cours final doit être rédigé en français clair et adapté à un
élève de seconde.
```

---

## 16. Prompt de structuration

```text
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
- écrire les formules en LaTeX ($...$ ou $$...$$).

Tu ne dois pas :
- reformuler les phrases de l'élève ;
- corriger une erreur de fond, même évidente ;
- ajouter une notion de cours absente ;
- inventer un exemple ;
- inventer une définition ;
- compléter toi-même une information manquante.

Si un passage est illisible ou incompréhensible, conserve-le tel quel.
Les erreurs de fond seront traitées séparément par l'analyse.

Retourne le résultat au format demandé.
```

---

## 17. Prompt d'analyse

```text
MATIÈRE
{{ subject }}

CHAPITRE
{{ chapter }}

NOTES STRUCTURÉES
{{ cleaned_course }}

DOCUMENTS DE RÉFÉRENCE
{{ reference_context }}

Recherche uniquement :
- erreurs probables ;
- contradictions ;
- notion manifestement incomplète ;
- définition manquante ;
- élément du cours qui semble mal compris ;
- information importante présente dans les références mais absente des notes.

Ne réécris pas le cours.

Retourne uniquement des suggestions structurées.

Pour chaque suggestion, "original_text" doit être recopié exactement
depuis les notes structurées, caractère pour caractère.

Si tu n'es pas certain, diminue le niveau de confiance.
```

---

## 18. Suggestions

L'élève ne reçoit jamais plus de **4 suggestions** par relecture, les plus importantes d'abord
(correction, avertissement, information manquante, clarification, puis complément), chacune
courte (1 à 2 phrases) ; un complément s'appuie toujours sur un document de référence. Moins
encore pour un élève qui se fatigue à lire. Cette limite est demandée à l'IA et vérifiée par le
serveur (`MAX_SUGGESTIONS`).

Exemple :

```text
⚠ À vérifier

Tu as noté :
"b est la pente"

Suggestion :
"a est le coefficient directeur et b est l'ordonnée à l'origine."

Pourquoi ?
La définition semble avoir été inversée.

[ Accepter ] [ Refuser ]
```

Complément :

```text
💡 Complément proposé

Une fonction linéaire est une fonction affine pour laquelle b = 0.

Cette information n'était pas présente dans tes notes.

[ Ajouter ] [ Ignorer ]
```

Ne pas dépendre uniquement de la couleur.

### 18.1 Application d'une suggestion acceptée

À la réception de l'analyse, le backend vérifie chaque suggestion :
- `original_text` trouvé dans la version analysée → conservée ;
- non trouvé (et non vide) → écartée et journalisée (l'IA a mal recopié).

À l'acceptation :
1. chercher `original_text` dans le cours courant ;
2. une seule occurrence → remplacer (ou insérer après, pour `addition`) et créer une version `suggestion_applied` ;
3. plusieurs occurrences → afficher les passages et laisser l'utilisateur choisir lequel ;
4. aucune occurrence → la suggestion passe à `outdated` et le texte proposé est affiché pour une copie manuelle.

Un `warning` n'a pas de texte à appliquer : l'accepter signifie seulement « vu ».

Ne jamais modifier le cours sans action explicite de l'utilisateur.

---

## 19. Fonction « Je n'ai pas compris »

Sur un passage sélectionné :

```text
[ Je n'ai pas compris ]
```

Envoyer :
- matière ;
- chapitre ;
- passage ;
- contexte ;
- niveau seconde.

Réponses possibles :
- Encore plus simple
- Donne-moi un exemple
- Pose-moi une question

---

## 20. Référentiel pédagogique

Structure :

```text
data/
  references/
    seconde/          (aussi premiere/ et terminale/ : le dossier de la classe)
      mathematiques/
      francais/
      histoire-geographie/
      svt/
      physique-chimie/
      ses/
      snt/
```

Métadonnées recommandées :
- title
- subject
- level
- school_year
- source
- url

V1 : recherche textuelle / SQLite FTS5.
Pas de grosse base vectorielle au départ.

---

## 21. Historique et audit

Conserver :
- entrée ;
- résultat ;
- date ;
- modèle utilisé ;
- suggestions ;
- décisions utilisateur.

Concrètement : versions `Course`, `AISuggestion` (statut + `decided_at`) et `AIRun`.

Toujours conserver les notes originales.

Modèle logique :

```text
SOURCE
notes originales

DERIVED
cours restructuré

SUGGESTIONS
propositions IA
```

---

## 22. Sauvegarde automatique

Sauvegarde quotidienne et restauration : voir « Ne rien perdre » dans le README.
`POST /api/backups/{nom}/restore` et `POST /api/backups/restore` (fichier) remplacent la base et
les images ; l'archive est vérifiée (forme, intégrité, version du schéma) puis l'état actuel
est sauvegardé avant le remplacement.

Sauvegarde du texte pendant la frappe :

Sauvegarder :
- après quelques secondes d'inactivité ;
- avant analyse IA ;
- avant changement de chapitre.

Afficher :
- Sauvegarde...
- Sauvegardé

---

## 23. Recherche

Recherche simple dans :
- titre ;
- matière ;
- contenu.

SQLite FTS5 suffisant.

---

## 24. Export

Minimum :
- Markdown
- PDF

Option :
- DOCX

Quiz : export au format d'import texte d'Anki (`GET /api/chapters/{id}/quiz/anki.txt`), une
carte par question (recto : question et propositions ; verso : réponse, explication, extrait du
cours), étiquette = matière.

Impression sobre : couleurs conservées (bordures, libellés, titres), pas de fond ni d'aplat
(économie d'encre), marges de 2,2 cm.

PDF : généré par le navigateur depuis une vue d'impression (`/chapitres/{id}/imprimer`),
pour un rendu exact des formules KaTeX sans moteur PDF côté serveur.

- titre ;
- matière ;
- chapitre ;
- date ;
- pagination ;
- bonne lisibilité ;
- formules correctement rendues.

---

## 25. Fiche de révision

La fiche doit tenir sur le moins de pages possible. « L'essentiel » n'existe que s'il apporte
quelque chose que la suite de la fiche ne montre pas déjà (jamais pour une liste de vocabulaire,
de dates ou de formules) ; plus de 4 définitions courtes tiennent dans un seul tableau « Mot |
Définition », pas dans un encadré par mot. Aucune balise HTML.

Bouton :
`Créer une fiche de révision`

Utiliser uniquement le cours courant (dernière version), jamais les suggestions en attente.

Sections possibles :
- À retenir
- Définitions
- Formules
- Dates importantes
- Personnes / notions importantes
- Exemple
- Points à savoir

---

## 26. Quiz

Types :
- QCM
- réponse courte
- vrai/faux

Générer uniquement depuis le cours courant (dernière version).

---

## 27. Confidentialité

Ne pas demander :
- nom complet ;
- date de naissance ;
- établissement ;
- adresse ;
- informations médicales.

Ne pas envoyer d'informations inutiles au provider IA.

### 27.1 Accès

Pas de comptes utilisateurs.

L'application est prévue pour un usage local ou sur le réseau domestique.
Comme la clé API est côté serveur, toute personne qui atteint l'application peut consommer le budget IA.

Si `APP_PASSWORD` est défini, toutes les routes `/api/*` sauf `/api/health` exigent ce mot de passe
(un seul mot de passe partagé, session par cookie `HttpOnly`).
Si `APP_PASSWORD` est vide, l'accès est libre ; un avertissement est loggé au démarrage quand `APP_ENV=production`.

Ne jamais exposer l'application sur Internet sans `APP_PASSWORD`.

---

## 28. OpenAI

Clé API OpenAI (Responses API), ou abonnement ChatGPT Plus/Pro : « Sign in with ChatGPT » (OAuth,
retour en boucle locale 127.0.0.1) délivre un jeton lié au plan, utilisé avec la même Responses API.
L'abonnement ne sert que pour un usage personnel ; un service hébergé pour des tiers utilise des clés API.

L'application doit fonctionner sans clé pour toutes les fonctions non IA.

Utiliser l'API OpenAI actuelle et garder le modèle configurable.

---

## 29. Maîtrise des coûts

Chaque appel IA est enregistré dans `AIRun` (voir §9) :
- provider ;
- modèle ;
- input_tokens ;
- output_tokens ;
- coût estimé.

Le coût estimé est calculé à partir de prix par million de tokens configurables ;
s'ils ne sont pas configurés, `estimated_cost_eur` reste vide.

Quand la somme des coûts du mois atteint `AI_MONTHLY_BUDGET_EUR`, les appels IA sont refusés
avec un message clair. Les fonctions non IA restent disponibles.

Variable :
```env
AI_MONTHLY_BUDGET_EUR=5
```

Prévoir un cache basé sur :
- texte ;
- matière ;
- chapitre ;
- version du prompt.

---

## 30. Gestion des erreurs

Traiter :
- API indisponible ;
- timeout ;
- clé invalide ;
- quota atteint ;
- réponse IA invalide ;
- budget mensuel atteint ;
- mot de passe incorrect ;
- problème de connexion ;
- SQLite verrouillée.

Le backend renvoie un code d'erreur stable (ex. `ai_timeout`, `ai_invalid_key`, `ai_budget_exceeded`)
et le frontend le traduit en message compréhensible.

Messages compréhensibles.

---

## 31. API REST

```text
GET    /api/health

POST   /api/auth/login
POST   /api/auth/logout

GET    /api/subjects

GET    /api/chapters
POST   /api/chapters
GET    /api/chapters/{id}
PATCH  /api/chapters/{id}
DELETE /api/chapters/{id}

GET    /api/chapters/{id}/notes
PUT    /api/chapters/{id}/notes

POST   /api/chapters/{id}/structure
POST   /api/chapters/{id}/analyze

GET    /api/chapters/{id}/suggestions
POST   /api/suggestions/{id}/accept
POST   /api/suggestions/{id}/reject

GET    /api/chapters/{id}/course
PUT    /api/chapters/{id}/course
GET    /api/chapters/{id}/course/versions
GET    /api/chapters/{id}/course/versions/{version}

POST   /api/chapters/{id}/revision-sheet
POST   /api/chapters/{id}/quiz

GET    /api/search
```

`GET /api/chapters/{id}/course` renvoie aussi `notes_changed` (hash des notes ≠ `source_notes_hash`).
`PUT /api/chapters/{id}/course` crée une version `user_edit`, il n'écrase rien.
Les routes `/api/auth/*` ne servent que si `APP_PASSWORD` est défini.

---

## 32. Structure du repository

```text
./
├── AGENT.md
├── README.md
├── docker-compose.yml
├── .env.example
├── .gitignore
├── Makefile
├── .github/workflows/
├── docs/
│   ├── SPEC.md
│   └── screenshots/
├── site/               (page GitHub Pages)
├── scripts/
│   ├── install.sh
│   └── install.ps1
│
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── api/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   │   ├── ai/
│   │   │   ├── course_service.py
│   │   │   ├── reference_service.py
│   │   │   └── export_service.py
│   │   └── prompts/
│   └── tests/
│
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── src/
│   └── tests/
│
└── data/
    └── references/
```

---

## 33. Tests

Backend :
- pytest
- ruff
- mypy

Frontend :
- eslint
- prettier
- TypeScript
- Vitest
- Playwright si utile

Aucun test ne doit effectuer de vrai appel OpenAI.

---

## 34. Docker

Démarrage attendu :

```bash
cp .env.example .env
docker compose up -d
```

Application :
```text
http://localhost:8080
```

Données persistantes dans `/data`.

Le conteneur frontend sert l'application compilée (nginx) sur le port 8080
et relaie `/api` vers le backend. Le backend n'est pas exposé directement.

Les migrations Alembic sont appliquées automatiquement au démarrage du backend.

---

## 35. Accessibilité

Prévoir :
- police lisible ;
- tailles de texte suffisantes ;
- boutons grands ;
- contraste correct ;
- navigation clavier ;
- labels explicites ;
- information jamais portée uniquement par la couleur.

Option :
- Normal
- Grand
- Très grand

Enfants dys (dyslexie, dyspraxie, TDAH…), par défaut et non en option : texte jamais sous
0,95 rem, ni justifié, ni en majuscules forcées, ni en italique ; lignes courtes ; cases à cocher
et boutons d'au moins 44 px. Réglages d'affichage : thème (clair, **crème**, sombre, comme
l'appareil), taille du texte, **espacement** des lettres et des mots. Contrôle automatique des
contrastes et des libellés par axe (`frontend/e2e/accessibility.spec.ts`), dans chaque thème.

---

## 36. Hors périmètre

Non prévu :
- application mobile native
- synchronisation cloud
- multi-établissements
- gestion professeur
- ENT
- Pronote
- reconnaissance avancée des photos (schémas, figures)
- collaboration temps réel
- dictée vocale et transcription audio
- grosse base vectorielle

---

## 37. Fonctionnalités

- « Je n'ai pas compris » (§19) ;
- providers d'IA : OpenAI, ChatGPT (abonnement), modèle local compatible OpenAI (Ollama, LM Studio) ;
- tests : pytest, Vitest, Playwright (`npm run e2e`, sur l'application lancée) ;
- consommation de l'IA dans les Réglages ;
- programmes officiels de toutes les classes (seconde à terminale, générale et technologique), téléchargés à la demande depuis le catalogue
  `backend/app/data/references_catalog.json` (aucun document officiel dans le dépôt) ;
- assistant de premier lancement (`/bienvenue`) : élève, puis choix et test de l'IA ; le choix
  est gardé dans `data/secrets/ai.enc` (chiffré, 0600) et l'emporte sur le `.env` (`/api/setup/*`) ;
- matières : catalogue commun (ajout, renommage, suppression si vide) et sélection par élève
  (`student_subjects`), préremplie selon la classe (`DEFAULTS_BY_LEVEL`), modifiable dans les
  Réglages ; le catalogue est créé au premier démarrage seulement (§8) ;
- plusieurs élèves par installation (Réglages → Élèves) : chapitres, recherche, corbeille et
  documents de référence séparés ; la classe (seconde, première, terminale) adapte les prompts ;
- cours en couleurs (encadrés, surlignage, schémas Mermaid, images), titre proposé,
  résumé lisible des modifications, impression soignée, éditeur visuel TipTap
  (le cours reste stocké en Markdown) ;
- photo des notes manuscrites (bouton « Photos des notes ») : photo redressée, réduite et
  réencodée sans métadonnées (EXIF, GPS) avant l'envoi à l'IA, puis conservée avec le chapitre ;
- protection des données : historique des notes (`note_versions`, 50 par chapitre),
  corbeille de 30 jours (`chapters.deleted_at`), sauvegarde quotidienne zip (base + images)
  dans `backups/`, 7 gardées, téléchargeable depuis les Réglages.
- téléphone : HTTPS optionnel par Caddy (profil `https`, autorité locale, certificat
  téléchargeable), application installable (manifeste, icônes, service worker sans cache
  des données), espace « Mes notes » vérifié sur un écran de téléphone.
- parcours en trois étapes (Mes notes → Mon cours → Réviser) : la relecture de l'IA (§18)
  est lancée après chaque mise au propre et s'affiche à côté du cours, avec les passages
  concernés surlignés dans le texte.

Pistes :
- programmes de la voie technologique hors séries courantes, options rares, programmes limitatifs ;
- tester sur de vrais cours de l'élève (qualité des prompts, des suggestions et des quiz) ;
- cache des réponses IA (§29) : l'empreinte `input_hash` est déjà enregistrée dans `AIRun` ;
- essayer le HTTPS et l'application installée sur le vrai téléphone de l'élève ;
- copie des sauvegardes hors de la machine (clé USB, NAS…), à faire à la main pour l'instant.
