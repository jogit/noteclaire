# Pistes pour la suite

Cette page garde des idées, pas des promesses : rien n'est daté ni garanti. Ce qui sera fait dépend
des retours sur la beta et du temps disponible. Les [issues](https://github.com/jogit/noteclaire/issues)
sont le bon endroit pour dire ce qui vous manque.

## D'abord : la beta

Faire installer NoteClaire par des gens qui ne l'ont pas écrit, et corriger ce qui coince :
l'installation (Linux, Mac, Windows), la qualité de la mise au propre selon les modèles, et le quotidien
des familles et des enseignants concernés.

## Peut-être un jour : une installation sans Docker

Docker est le principal frein pour des familles peu techniques. Une application de bureau
(un installeur Windows, puis macOS) est une piste sérieuse : un essai existe et fonctionne, mais il
demande une signature de code (sans elle, certains antivirus et navigateurs le signalent) et un test
sur de vrais ordinateurs. Il n'est donc pas publié.

Dans le prolongement :
- une **application Android** pour photographier les notes avec l'appareil photo du téléphone et les
  envoyer à l'ordinateur de la maison (association par QR code) ;
- le **HTTPS intégré** pour la caméra du navigateur sur téléphone (aujourd'hui : un reverse proxy, voir
  [Configuration](docs/configuration.md#derrière-un-reverse-proxy)).

## Plus tard, si le besoin se confirme

- Un **code par élève**, pour une vraie séparation entre enfants (aujourd'hui, changer d'élève dans le
  navigateur reste libre).
- Le **message de bienvenue** que recommande OpenAI à la première connexion avec l'abonnement ChatGPT.
- Un **site de documentation** (recherche, navigation) et une vidéo de démonstration.

## Ce qui n'est pas prévu

- Une **réécriture en application native** : l'interface actuelle fait déjà le travail, et refaire
  l'éditeur, les formules et les schémas en natif coûterait des mois pour le même résultat.
- Un **service hébergé** où l'on s'inscrit sans rien installer : héberger les notes d'élèves mineurs
  engage la responsabilité de l'hébergeur (RGPD), et OpenAI traite les applications hébergées à
  distance autrement que les applications locales (voir [Abonnement ChatGPT](docs/openai.md)).
