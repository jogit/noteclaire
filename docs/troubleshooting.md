# Dépannage

## Docker

**« error getting credentials … docker-credential-desktop.exe: exec format error »** (WSL)
Le trousseau de Docker Desktop n'est pas joignable depuis WSL. Ouvrez `~/.docker/config.json` et
supprimez la ligne `"credsStore": "desktop.exe"` (ou `"credsStore": "desktop"`), puis relancez.

**« port is already allocated » / « Bind for 0.0.0.0:8080 failed »**
Une autre application utilise le port 8080. Ajoutez `HTTP_PORT=8081` dans `.env` (dossier
`~/noteclaire`) et relancez la commande d'installation.

**Docker ne répond pas**
Lancez Docker Desktop (Windows, Mac) ou le service (`sudo systemctl start docker`, Linux), attendez
qu'il soit prêt, puis recommencez.

## Utilisation

**J'ai perdu le mot de passe.**
Il est dans le fichier `.env` du dossier d'installation (`APP_PASSWORD=`). Vous pouvez le changer :
modifiez la ligne, puis `docker compose up -d`. Tous les appareils devront se reconnecter.

**Il n'y a pas de bouton « Continue with ChatGPT », seulement une adresse.**
OpenAI n'accepte la connexion que depuis l'ordinateur qui héberge NoteClaire, ouvert à l'adresse
`http://127.0.0.1:8080` (pas `localhost`). Ouvrez cette adresse sur cet
ordinateur (voir [Configuration](configuration.md)) ; la connexion ne se fait qu'une fois.

**« Prendre une photo » n'affiche pas d'aperçu de la caméra.**
Le navigateur n'autorise l'aperçu en direct qu'en HTTPS. Sans HTTPS, le bouton ouvre l'appareil photo
du téléphone, puis NoteClaire reçoit la photo : tout fonctionne, seul l'aperçu manque. Voir
[Configuration](configuration.md#derrière-un-reverse-proxy) pour publier NoteClaire en HTTPS.

**« La base de données est occupée »**
Un autre processus utilise la base au même moment (une sauvegarde, par exemple). Réessayez dans un
instant.

## Voir ce qui se passe

```bash
cd ~/noteclaire
docker compose ps          # état des conteneurs
docker compose logs -f     # journaux en direct
```

Pour tout arrêter : `docker compose down` (ajoutez `-v` pour effacer aussi les données).
