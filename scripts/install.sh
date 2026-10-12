#!/bin/sh
# Installe (ou met à jour) NoteClaire : télécharge la configuration, choisit un mot de passe,
# lance l'application. À relancer à tout moment pour mettre à jour : rien n'est écrasé.
#
#   curl -fsSL https://raw.githubusercontent.com/jogit/noteclaire/main/scripts/install.sh | sh
#
# Variables facultatives : NOTECLAIRE_DIR (dossier, ~/noteclaire par défaut), NOTECLAIRE_CHATGPT=oui|non
# (abonnement ChatGPT pour l'IA), NOTECLAIRE_RAW (adresse des fichiers).
set -eu

RAW="${NOTECLAIRE_RAW:-https://raw.githubusercontent.com/jogit/noteclaire/main}"
DIR="${NOTECLAIRE_DIR:-$HOME/noteclaire}"

say() { printf '%s\n' "$*"; }
fail() { printf '\n✗ %s\n' "$*" >&2; exit 1; }

command -v docker >/dev/null 2>&1 ||
  fail "Docker n'est pas installé. Installez-le d'abord : https://docs.docker.com/get-docker/"
docker compose version >/dev/null 2>&1 ||
  fail "Il manque « docker compose » (version 2). Mettez Docker à jour : https://docs.docker.com/get-docker/"
docker info >/dev/null 2>&1 ||
  fail "Docker est installé mais ne répond pas. Lancez Docker Desktop (ou le service docker), puis recommencez."

mkdir -p "$DIR"
cd "$DIR"
say "Dossier de NoteClaire : $DIR"

COMPOSE_TMP="docker-compose.yml.tmp.$$"
trap 'rm -f "$COMPOSE_TMP"' EXIT HUP INT TERM
if [ -n "${NOTECLAIRE_COMPOSE:-}" ]; then
  cp "$NOTECLAIRE_COMPOSE" "$COMPOSE_TMP" ||
    fail "Lecture de la configuration locale impossible : $NOTECLAIRE_COMPOSE"
else
  curl -fsSL "$RAW/docker-compose.yml" -o "$COMPOSE_TMP" ||
    fail "Téléchargement impossible : vérifiez la connexion à Internet."
fi
# Ne remplace jamais une configuration fonctionnelle par un téléchargement incomplet ou invalide.
APP_PASSWORD=validation docker compose -f "$COMPOSE_TMP" config --quiet >/dev/null 2>&1 ||
  fail "La configuration téléchargée est invalide ; l'ancienne installation est conservée."
mv "$COMPOSE_TMP" docker-compose.yml

# Une réponse oui/non : la valeur préréglée $1 si elle existe, sinon la question $2 posée à l'écran,
# « non » quand il n'y a personne pour répondre.
ask() {
  if [ -n "$1" ]; then answer="$1"
  elif [ -r /dev/tty ]; then printf '%s [o/N] ' "$2" >/dev/tty; read -r answer </dev/tty || answer=n
  else answer=n; fi
  case "$answer" in o|O|oui|OUI|y|Y|yes) return 0 ;; *) return 1 ;; esac
}

PASSWORD=""
CHATGPT=""
if [ ! -f .env ]; then
  PASSWORD="$(LC_ALL=C tr -dc 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789' </dev/urandom | head -c 12)"
  {
    echo "# Réglages de NoteClaire (voir .env.example pour les options)."
    echo "APP_PASSWORD=$PASSWORD"
  } > .env
  if ask "${NOTECLAIRE_CHATGPT:-}" "Utiliser votre abonnement ChatGPT Plus ou Pro pour l'IA (sinon : clé OpenAI ou IA locale, à choisir ensuite) ?"; then
    echo "AI_PROVIDER=chatgpt" >> .env
    CHATGPT=1
  fi
  chmod 600 .env
else
  say "Un fichier .env existe déjà : il est conservé (mise à jour)."
  PASSWORD="$(sed -n 's/^APP_PASSWORD=//p' .env | head -n 1)"
  [ "$(sed -n 's/^AI_PROVIDER=//p' .env | head -n 1)" != chatgpt ] || CHATGPT=1
fi
chmod 600 .env

say "Téléchargement et démarrage (quelques minutes la première fois)…"
docker compose pull -q || say "(images non téléchargées : utilisation de celles déjà présentes)"
docker compose up -d ||
  fail "Le démarrage a échoué. Si le message parle d'un port déjà utilisé, ajoutez HTTP_PORT=8081 dans $DIR/.env puis relancez cette commande."

PORT="$(sed -n 's/^HTTP_PORT=//p' .env | head -n 1)"
PORT="${PORT:-8080}"
say "Attente du démarrage…"
i=0
until curl -fs "http://127.0.0.1:$PORT/api/health" >/dev/null 2>&1; do
  i=$((i + 1))
  [ "$i" -le 60 ] || fail "NoteClaire ne répond pas. Voyez : cd $DIR && docker compose logs"
  sleep 2
done

URL="http://127.0.0.1:$PORT"
say ""
say "✓ NoteClaire est prêt : $URL"
if [ -n "$PASSWORD" ]; then
  say "  Mot de passe : $PASSWORD   (gardé dans $DIR/.env)"
fi
if [ -n "$CHATGPT" ]; then
  say "  Connexion ChatGPT : à faire une seule fois, depuis cet ordinateur et à l'adresse $URL"
  say "  (OpenAI n'accepte que 127.0.0.1) ; ensuite tous les appareils de la maison l'utilisent."
fi
say "  Mettre à jour : relancez cette commande. Arrêter : cd $DIR && docker compose down"

if command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL" >/dev/null 2>&1 || true
elif command -v open >/dev/null 2>&1; then open "$URL" >/dev/null 2>&1 || true; fi
