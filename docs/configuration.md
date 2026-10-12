# Configuration

Les réglages se font dans le fichier `.env` (modèle : [`.env.example`](../.env.example)). Seul
`APP_PASSWORD` compte vraiment ; le choix de l'IA se fait dans l'application, au premier lancement.
Après une modification : `docker compose up -d`.

## Choix de l'IA

L'assistant de premier lancement (ou Réglages → Intelligence artificielle) propose quatre options
et teste la connexion. La clé saisie est chiffrée dans `data/secrets/`, jamais réaffichée, et
l'emporte sur `OPENAI_API_KEY` du `.env`.

### Clé OpenAI

La plus simple. Le coût du mois est estimé à partir des prix du modèle
(`AI_INPUT_PRICE_EUR_PER_MTOK`, `AI_OUTPUT_PRICE_EUR_PER_MTOK`) et plafonné par
`AI_MONTHLY_BUDGET_EUR` (5 € par défaut, 0 = sans limite). La consommation se voit dans
Réglages → Avancé.

### Abonnement ChatGPT (« Sign in with ChatGPT »)

Avec un abonnement Plus ou Pro, l'IA peut utiliser l'abonnement au lieu d'une clé API (usage
autorisé par OpenAI pour les projets personnels qui tournent en local) :

1. répondre « o » à la question du script d'installation (il écrit `AI_PROVIDER=chatgpt` dans `.env`
   et ouvre `http://127.0.0.1:8080`), ou le choisir dans l'assistant ou dans `.env` ;
2. dans Réglages → « Continue with ChatGPT » (ou à la fin de l'assistant de démarrage) ;
3. se connecter sur chatgpt.com et autoriser NoteClaire : on revient sur les Réglages, où l'on choisit
   le modèle.

Ensuite, tous les appareils de la maison utilisent l'IA via ce compte. L'écran affiche « Using
ChatGPT plan » avec un lien « Manage usage » vers les réglages d'utilisation de ChatGPT, où l'on
limite la consommation. Les jetons sont chiffrés dans `data/secrets/` (exclu des sauvegardes et de
git), avec une clé rangée à côté : cela évite les fuites accidentelles, pas l'accès de quelqu'un qui
contrôle déjà la machine.

**Pourquoi depuis l'ordinateur hôte, à l'adresse `127.0.0.1` ?** OpenAI n'accepte, pour ce type
d'application, que le retour de connexion sur `http://127.0.0.1:<port>/auth/callback` (boucle locale :
pas `localhost`, pas une adresse du réseau ; seul le port peut varier). Ce retour atteint la machine
où tourne le navigateur : la connexion se fait donc une seule fois, dans un navigateur ouvert sur
l'ordinateur qui héberge NoteClaire, à l'adresse `http://127.0.0.1:8080` (ou le `HTTP_PORT`
choisi). Les autres appareils de la maison n'ont rien à faire : ils utilisent l'IA via ce compte.
Si NoteClaire est ouvert par une autre adresse (`localhost`, nom de domaine, HTTPS, autre appareil),
le bouton est remplacé par un rappel de l'adresse à utiliser. Si NoteClaire tourne sur un serveur sans
écran, ouvrez un tunnel SSH (`ssh -L 8080:127.0.0.1:8080 serveur`) puis `http://127.0.0.1:8080` sur
votre poste. Si `CHATGPT_REDIRECT_PORT` ne correspond pas au port de l'application, la connexion
échoue.

**Derrière un reverse proxy.** La connexion se fait toujours sur l'ordinateur hôte, à
`http://127.0.0.1:<HTTP_PORT>`, même si les autres appareils passent par le proxy : gardez donc ce port
accessible depuis cet ordinateur. Pour qu'il ne le soit pas depuis le réseau, limitez-le par le
pare-feu, ou liez-le à l'ordinateur seul avec un fichier `docker-compose.override.yml` à côté de
`docker-compose.yml` (Docker Compose 2.24 ou plus) :

```yaml
services:
  frontend:
    ports: !override
      - "127.0.0.1:8080:8080"
```

### IA locale (Ollama, LM Studio)

Gratuit, et rien ne sort de la maison. Un serveur compatible OpenAI suffit :

```env
AI_PROVIDER=local
LOCAL_AI_BASE_URL=http://host.docker.internal:11434/v1   # Ollama ; LM Studio : port 1234
LOCAL_AI_MODEL=qwen3:8b
```

Installez Ollama (ou LM Studio) sur l'ordinateur, téléchargez un modèle (`ollama pull qwen3:8b`) :
NoteClaire le joint depuis Docker via `host.docker.internal`. Si Ollama tourne sur une autre machine,
remplacez l'adresse par la sienne.

La qualité dépend du modèle : un petit modèle (1 à 3 milliards de paramètres) peut perdre une
partie des notes, et l'application l'affiche alors en avertissement. Visez au moins 8 milliards de
paramètres. Le modèle doit savoir lire les images pour la lecture des photos (ex. `qwen2.5-vl`).

### Essayer sans IA

« Essayer sans IA » (`AI_PROVIDER=fake`) renvoie les notes telles quelles : utile pour découvrir
l'interface.

## Programmes et documents de référence

La relecture s'appuie sur les documents de la matière et de la classe de l'élève, indexés en plein
texte (SQLite FTS5). Chaque élève n'utilise que les documents de sa classe.

Le bouton **« Télécharger les programmes officiels »** (page Documents) récupère ceux de la classe
de l'élève depuis les sites officiels (Bulletin officiel, eduscol). Internet est nécessaire et rien
n'est téléchargé sans ce clic. Le catalogue (`backend/app/data/references_catalog.json`) couvre :

- la **seconde** générale et technologique : 11 matières, plus les options (sciences de
  l'ingénieur, création et innovation technologiques, management et gestion, biotechnologies,
  création et culture-design, danse-musique-théâtre) et la seconde STHR ;
- la **voie générale** en première et terminale ;
- la **voie technologique** en première et terminale : tronc commun, plus une matière par série
  (STMG, STI2D, STL, ST2S, STD2A, S2TMD, STHR) qui regroupe les programmes de cette série.

Les options et spécialités rares ne sont pas dans le catalogue : ajoutez-les à la main (ci-dessous)
ou ajoutez une entrée au catalogue (`level`, `subject`, `title`, `source`, `school_year`, `url`
d'un PDF).

**Vérifiez que les programmes sont à jour.** Le catalogue reprend la rubrique « Programmes en
vigueur » d'eduscol, relevée en octobre 2026. NoteClaire ne vérifie pas l'année de mise en vigueur : si
un programme change, remplacez le document ou corrigez l'adresse dans le catalogue.

**Ajouter ses propres documents** : depuis la page Documents, ou en les déposant dans
`data/references/<classe>/<matière>/` (classes : `seconde`, `premiere`, `terminale`,
`premiere-techno`, `terminale-techno` ; formats PDF, `.md`, `.txt`) puis « Relire le dossier »
(ils sont aussi relus à chaque démarrage). Métadonnées facultatives : en-tête `---` en Markdown
(`title`, `source`, `url`, `school_year`) ou fichier voisin `<nom du fichier>.meta.json`.

## Derrière un reverse proxy

NoteClaire écoute en HTTP sur `HTTP_PORT` (8080 par défaut). Pour le publier en HTTPS, placez-le
derrière votre proxy (Traefik, Nginx Proxy Manager, nginx, Caddy…) qui pointe vers
`http://<ordinateur>:8080`, ou vers `frontend:8080` s'il est dans le même réseau Docker. Réglages à
respecter côté proxy :

- transmettre `Host`, `X-Forwarded-For` et surtout **`X-Forwarded-Proto: https`** : NoteClaire s'en
  sert pour réserver le cookie de session à HTTPS ;
- autoriser des envois d'**au moins 60 Mo** (photos), et **2 Go** pour la restauration d'une
  sauvegarde (`/api/backups/restore`) ;
- un délai de lecture d'**au moins 300 secondes** : la mise au propre par l'IA peut être longue.

Définissez `APP_PASSWORD` dès que l'application est accessible depuis le réseau.

## Variables

| Variable | Défaut | Rôle |
| --- | --- | --- |
| `APP_PASSWORD` | vide | Mot de passe d'accès (obligatoire si d'autres appareils s'y connectent) |
| `NOTECLAIRE_VERSION` | `latest` | Version des images à installer |
| `HTTP_PORT` | `8080` | Port de l'application sur la machine |
| `AI_PROVIDER` | `openai` | `openai`, `chatgpt`, `local` ou `fake` |
| `OPENAI_API_KEY`, `OPENAI_MODEL` | vide, `gpt-6-luna` | Clé et modèle OpenAI |
| `LOCAL_AI_BASE_URL`, `LOCAL_AI_MODEL` | voir `.env.example` | Serveur et modèle locaux |
| `AI_MONTHLY_BUDGET_EUR` | `5` | Plafond mensuel (0 = sans limite) |
| `AI_INPUT_PRICE_EUR_PER_MTOK`, `AI_OUTPUT_PRICE_EUR_PER_MTOK` | `0.09`, `0.45` | Prix pour estimer les coûts |
| `BACKUP_KEEP` | `7` | Nombre de sauvegardes quotidiennes gardées |
