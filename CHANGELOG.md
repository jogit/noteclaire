# Journal des versions

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
