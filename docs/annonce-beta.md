# Texte d'annonce de la beta

Brouillon à adapter selon le lieu de publication (r/selfhosted, LinuxFR, associations dys). Ne pas
publier tel quel sans l'avoir relu : les parties entre crochets sont à compléter.

---

## Titre

NoteClaire (beta) : un assistant auto-hébergé pour remettre au propre ses notes de cours, pensé pour
les lycéens dys

## Texte

Bonjour,

je publie la première beta de **NoteClaire**, une application web que l'on héberge chez soi
(Docker). Un lycéen tape ou photographie ses notes de cours, et une IA les remet au propre **sans
jamais les remplacer** : elle structure, corrige ce qui est douteux et propose des compléments à part,
que l'élève accepte ou refuse un par un. Elle sait aussi faire une fiche de révision, un quiz et un
export Anki.

**Pour qui ?** Les lycéens (seconde à terminale, voies générale et technologique), et en particulier
ceux qui ont un trouble « dys » : police Lexend, thème crème, espacement réglable, contrastes
contrôlés, explications adaptées aux particularités renseignées. Je ne prétends pas que c'est un outil
thérapeutique : c'est un confort de lecture et de révision.

**Comment ça marche ?**
- Photos de cahier lues par l'IA (mots douteux signalés), schémas découpés et redessinables.
- Relecture appuyée sur les programmes officiels de l'Éducation nationale, avec la source citée.
- Un espace par enfant, historique des versions, corbeille de 30 jours, sauvegardes quotidiennes.
- IA au choix : clé OpenAI, abonnement ChatGPT, ou modèle local (Ollama, LM Studio).

**Installation** (Docker nécessaire) :

```
curl -fsSL https://raw.githubusercontent.com/jogit/noteclaire/main/scripts/install.sh | sh
```

Windows : `irm https://raw.githubusercontent.com/jogit/noteclaire/main/scripts/install.ps1 | iex`

**Ce que c'est, honnêtement : une beta.**
- Pas de HTTPS intégré (derrière un reverse proxy si vous voulez en avoir), donc sur téléphone la
  photo passe par l'appareil photo du système, sans aperçu en direct.
- Pas de code par enfant : changer d'élève dans le navigateur reste libre.
- Le script d'installation Windows est peu testé.
- Les programmes officiels sont à vérifier à chaque rentrée.
- La connexion à l'abonnement ChatGPT se fait une fois, depuis l'ordinateur qui héberge NoteClaire
  (exigence d'OpenAI), et cette fonction est elle-même présentée comme une préversion par OpenAI.

**Vie privée.** Tout reste chez vous (base SQLite, photos, sauvegardes), sans compte, sans
statistiques, sans service centralisé. Seul ce qui est envoyé à l'IA que vous choisissez quitte la
maison, et rien du tout avec une IA locale. Le détail, y compris le fait que les « particularités »
de l'élève peuvent être des données de santé : docs/vie-privee.md.

**Licence** AGPL-3.0. [Mention de l'aide d'assistants IA pour le développement, relu et testé par
l'auteur : à confirmer et à adapter.]

Code, documentation et page de présentation : https://github.com/jogit/noteclaire et
https://jogit.github.io/noteclaire/

Je cherche surtout des retours sur **l'installation** (Linux, Mac, Windows), la **qualité de la mise
au propre** avec différents modèles, et les **réalités du quotidien** des familles et enseignants
concernés. Les issues GitHub sont ouvertes.

---

## Réponses courtes pour les commentaires

**« Et les données de mon enfant ? »** → Elles restent sur votre machine. Seul le texte des notes (et
la classe et les particularités renseignées) part vers l'IA que vous choisissez ; avec une IA locale,
rien ne sort. Le prénom n'est jamais envoyé. Détail : docs/vie-privee.md.

**« Ça utilise mon abonnement ChatGPT, c'est autorisé ? »** → OpenAI documente cet usage pour les
applications open source hébergées en local, en préversion. Ce que NoteClaire respecte et ce qu'il
reste à vérifier de votre côté (conditions, partage de compte, âge) : docs/openai.md. Une clé API ou
une IA locale marchent aussi.

**« Pourquoi pas de HTTPS ? »** → Pas dans cette beta, pour garder l'installation simple. Un reverse
proxy suffit : docs/configuration.md.

**« L'IA ne fait pas le travail à la place de l'élève ? »** → Non, c'est le principe : elle garde ses
notes, signale ce qui semble faux ou manquant dans une liste de suggestions, et ne modifie rien
sans qu'il accepte.
