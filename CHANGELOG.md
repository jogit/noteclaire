# Journal des versions

## 0.1.0-beta.2

Consignes données à l'IA revues de bout en bout, et garde-fous côté serveur pour que l'IA ne
puisse plus modifier le cours de l'élève en silence.

### Améliorations
- **Relecture** : l'IA complète elle-même les passages restés incomplets (phrase coupée, « … »,
  valeur non terminée) au lieu de renvoyer vers le professeur, avec une confiance basse quand
  elle n'est pas sûre et l'origine de la suite indiquée. Jusqu'à 6 suggestions, les passages
  incomplets passent avant les simples avertissements.
- **Fiche de révision** : la frise chronologique n'apparaît qu'avec au moins 3 dates, et
  l'encadré « À vérifier » dit de quel sujet il s'agit et ce qui manque, avec quelques mots
  du cours pour retrouver le passage.
- **Mise au propre** : un cours résumé, réécrit ou complété par l'IA est refusé et relancé une
  fois, au lieu d'être enregistré.
- **Particularité « dysorthographie »** : les fautes d'orthographe sont corrigées sans être
  signalées.
- Les textes de l'élève (notes, cours, remarques, particularités) sont délimités dans les
  consignes : un texte qui prétend donner des ordres à l'IA est traité comme du contenu.

### Corrections
- Un complément qui cite un document de référence inconnu, ou une question de quiz dont
  l'extrait justificatif n'est pas dans le cours, n'est plus gardé.
- Développement : les consignes modifiées sont prises en compte sans redémarrer le serveur, et
  la connexion ChatGPT revient sur le bon port.

### Limites connues
- Les nouvelles consignes ont surtout été éprouvées avec l'abonnement ChatGPT. Avec un petit
  modèle local, la mise au propre peut être refusée plus souvent par le contrôle de fidélité
  (nouvelle tentative automatique, puis message d'erreur).
- Les limites de la bêta précédente restent valables (voir plus bas).

## 0.1.0-beta.1

Première version publique, en bêta : utilisable en famille, à essayer avant de la recommander
largement (voir « Limites connues »).

### Fonctionnalités
- Notes au clavier ou **photos de cahier** (plusieurs pages) lues par l'IA, avec mots douteux
  signalés ; schémas découpés automatiquement et redessinables.
- **Mise au propre** du cours en Markdown (encadrés, formules, schémas), comparaison avec les notes,
  éditeur visuel, versions, export PDF et Markdown.
- **Relecture** par l'IA, suggestion par suggestion, appuyée sur les **programmes officiels**
  (seconde à terminale, voies générale et technologique) téléchargés à la demande ; « Je n'ai pas
  compris ».
- **Fiche de révision**, **quiz** et export Anki.
- Un **espace par enfant** (classe, matières, particularités), données séparées côté serveur.
- Historique des notes, corbeille de 30 jours, sauvegardes quotidiennes vérifiées.
- IA au choix : clé OpenAI, abonnement ChatGPT (« Continue with ChatGPT »), ou modèle local.
- Interface pensée pour les élèves dys : police Lexend, thème crème, espacement réglable,
  contrastes contrôlés dans chaque thème.
- Installation en une commande (Linux, Mac, Windows).

### Limites connues
- Changer d'élève dans le navigateur reste libre (pas de code par élève).
- La connexion ChatGPT se fait depuis l'ordinateur qui héberge NoteClaire (exigence d'OpenAI).
- Le script d'installation Windows est peu testé.
- Pas de HTTPS intégré : sur le téléphone, la photo passe par l'appareil photo du système, sans
  aperçu en direct (voir « Derrière un reverse proxy » pour publier en HTTPS).
- Les programmes officiels sont à vérifier à chaque rentrée.
