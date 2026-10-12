# Vie privée : ce qui reste chez vous, ce qui sort

NoteClaire est auto-hébergé : il tourne sur votre ordinateur et garde ses données dans vos volumes
Docker. Il n'y a ni compte, ni serveur central, ni statistiques d'usage, ni police ou script chargé
depuis un autre site : le code ne contient aucun appel vers un service de suivi. Ce document dit
précisément ce qui quitte la maison, et dans quel cas.

## Ce qui reste chez vous

- Les **notes, cours, fiches, quiz, photos de cahier et schémas**, dans la base SQLite et le dossier
  de données (volume `noteclaire-data`).
- Les **élèves** : prénom, classe, matières, particularités.
- Les **sauvegardes** quotidiennes (volume `noteclaire-backups`), qui contiennent tout ce qui précède,
  photos comprises : protégez-les comme le reste.
- Les **clés et jetons** (clé OpenAI, connexion ChatGPT), chiffrés dans `data/secrets/` avec une clé
  rangée à côté. Cela évite les fuites accidentelles (copie de la base, sauvegarde), pas l'accès de
  quelqu'un qui contrôle déjà la machine.

## Ce qui sort, et vers qui

### 1. Vers l'IA que vous avez choisie

Pour mettre un cours au propre, le relire, lire une photo, faire une fiche, un quiz ou répondre à
« Je n'ai pas compris », NoteClaire envoie à l'IA :

- le **texte des notes** ou du cours, ou la **photo** du cahier (les métadonnées de l'image, dont la
  position GPS, sont retirées avant l'envoi) ;
- le **titre du chapitre**, la **matière** et la **classe** ;
- les **particularités de l'élève** (par exemple dyslexie : les cases cochées et le texte libre), pour
  adapter les explications ;
- des **extraits des programmes officiels** téléchargés, pour que la relecture cite sa source.

NoteClaire **n'envoie pas** : le prénom de l'élève, le mot de passe, les autres élèves, les autres
chapitres. Attention toutefois à ce que l'élève écrit lui-même : un prénom tapé dans une note part avec
la note.

Selon l'IA choisie :

| Choix | Où vont ces données |
| --- | --- |
| Clé OpenAI | À OpenAI (API). NoteClaire demande de ne pas conserver les réponses (`store: false`). |
| Abonnement ChatGPT | À OpenAI, avec votre abonnement (voir [Abonnement ChatGPT et conditions d'OpenAI](openai.md)). Même demande de non-conservation. |
| IA locale (Ollama, LM Studio) | **Nulle part** : tout reste sur votre réseau. |
| « Essayer sans IA » | Nulle part. |

Ce que le fournisseur conserve ou utilise de son côté dépend de **ses** conditions et de **sa**
politique de confidentialité, pas de NoteClaire : lisez-les avant de choisir. `store: false` demande à
OpenAI de ne pas garder la réponse pour la consulter plus tard ; ce n'est pas une garantie sur tout
ce qu'OpenAI peut faire des données selon ses propres règles.

### 2. Vers les sites de l'Éducation nationale

À la demande seulement (bouton de téléchargement des programmes) : NoteClaire télécharge les
programmes officiels depuis `eduscol.education.gouv.fr`, `www.education.gouv.fr` et
`cache.media.education.gouv.fr`. Aucune donnée de l'élève n'est envoyée dans ces requêtes.

### 3. Vers OpenAI pour la connexion ChatGPT

La connexion ouvre `chatgpt.com` et `auth.openai.com` dans le navigateur, et NoteClaire échange des
jetons avec `auth.openai.com`. Elle n'a pas accès à vos conversations ChatGPT.

### 4. Pour l'installation

Le script d'installation télécharge des fichiers depuis `raw.githubusercontent.com` (configuration)
et les images depuis `ghcr.io` (GitHub). Rien d'autre n'est envoyé.

## Les particularités de l'élève sont des données sensibles

Le champ « particularités » (dyslexie, TDAH…) peut révéler des informations de santé, que le RGPD
protège davantage. Elles servent à adapter les explications et partent à l'IA avec les demandes.
Vous pouvez :

- ne cocher que ce qui est utile, et laisser le texte libre vide ;
- utiliser une **IA locale**, avec laquelle rien ne sort ;
- ne rien renseigner : NoteClaire fonctionne sans.

## Un usage familial, ou pas

Hébergé chez vous pour vos enfants, NoteClaire relève d'un usage domestique. S'il est hébergé par
un établissement, une association ou un professionnel pour des élèves, ce n'est plus le même cadre :
il y a alors un responsable de traitement, des obligations d'information et de durée de conservation
(et, pour l'abonnement ChatGPT, des conditions différentes : voir [openai.md](openai.md)). Parlez-en à
la personne qui s'occupe de la protection des données chez vous. Ce document n'est pas un avis
juridique.

## Limites à connaître

- **Pas de HTTPS intégré** : sur le Wi-Fi de la maison, les échanges entre le navigateur et NoteClaire
  ne sont pas chiffrés. Pour les chiffrer, placez NoteClaire derrière un reverse proxy
  (voir [Configuration](configuration.md#derrière-un-reverse-proxy)).
- **Un seul mot de passe partagé**, et changer d'élève dans le navigateur reste libre : ce n'est pas
  une séparation de sécurité entre enfants.
- Les sauvegardes et la corbeille (30 jours) conservent des données que vous croyez peut-être
  supprimées.

## Supprimer ses données

- Un chapitre supprimé reste 30 jours dans la corbeille, puis disparaît.
- Pour **tout** effacer : `docker compose down -v` dans le dossier d'installation supprime les volumes
  (données et sauvegardes). C'est définitif : faites une copie avant si vous en avez besoin.
- Pour retirer l'accès de NoteClaire à votre compte ChatGPT : « Se déconnecter » dans Réglages, puis
  retirez NoteClaire dans les réglages de ChatGPT.
