# Abonnement ChatGPT et conditions d'OpenAI

NoteClaire peut utiliser un abonnement ChatGPT Plus ou Pro au lieu d'une clé API (« Continue with
ChatGPT »). Cette page résume ce que dit OpenAI de cet usage, ce que NoteClaire en respecte, et ce
qu'il vous reste à vérifier vous-même. Ce n'est pas un avis juridique, et les règles d'OpenAI peuvent
changer : les liens renvoient aux sources, consultées le 12 octobre 2026.

## Ce que dit OpenAI

D'après la documentation de [Sign in with ChatGPT](https://developers.openai.com/siwc/token-sharing-open-source)
pour les applications open source :

- l'usage de l'abonnement est une **fonction optionnelle** : les requêtes éligibles passent par le
  plan ChatGPT de la personne qui se connecte ;
- il **ne donne pas accès** à ses conversations ChatGPT ni au reste de son compte ;
- la documentation couvre les applications **open source et hébergées en local** ; pour une
  application **payante ou hébergée à distance**, OpenAI renvoie vers un formulaire d'intérêt ;
- les limites d'utilisation sont **celles du plan** : elles se gèrent dans les réglages d'utilisation
  de ChatGPT ;
- l'adresse de retour de la connexion est **`http://127.0.0.1:<port>/auth/callback`**, et seulement
  celle-là ;
- l'utilisateur donne son accord à OpenAI lors de la connexion.

## Ce que cette documentation ne dit pas

Elle ne détaille ni les **conditions d'éligibilité** (qui peut utiliser son abonnement ainsi), ni ce
qu'OpenAI **conserve ou utilise** pour ces requêtes. Pour cela, il faut lire les
[conditions d'utilisation](https://openai.com/policies/terms-of-use) et la
[politique de confidentialité](https://openai.com/policies/privacy-policy) d'OpenAI, ainsi que les
réglages de données de votre compte ChatGPT.

## Ce que NoteClaire respecte

- La connexion se fait **sur l'ordinateur qui héberge NoteClaire**, à `127.0.0.1` : voir
  [Configuration](configuration.md#abonnement-chatgpt-sign-in-with-chatgpt).
- Le bouton s'appelle « Continue with ChatGPT », et l'écran affiche « Using ChatGPT plan » avec un
  lien « Manage usage » vers les réglages d'utilisation de ChatGPT, comme le demandent les
  [recommandations d'interface](https://developers.openai.com/siwc/ui-ux-guidelines).
- Les requêtes sont envoyées avec `store: false`, et l'identifiant de l'installation est opaque (il ne
  contient ni e-mail ni nom).
- Les jetons sont chiffrés au repos et ne sont jamais renvoyés au navigateur.

**Pas encore fait :** le message de bienvenue à la première connexion (« You're using your ChatGPT
plan ») que recommandent ces mêmes recommandations.

## Ce qu'il vous reste à vérifier

1. **Hébergement.** NoteClaire est pensé pour une famille qui l'héberge chez elle. Le proposer à
   d'autres personnes (établissement, association, service payant) revient à une application hébergée
   à distance : voir le formulaire d'intérêt d'OpenAI avant de le faire.
2. **Un compte pour toute la famille.** Un seul abonnement sert tous les enfants, et leurs demandes
   passent par le compte de la personne qui s'est connectée : les limites du plan sont partagées.
   Vérifiez dans les conditions d'OpenAI ce qui concerne le partage d'un compte et l'âge des
   utilisateurs. Les enfants n'ouvrent jamais ChatGPT, mais leurs demandes partent sous ce compte.
3. **Fonction en aperçu.** OpenAI présente cet usage comme une préversion, qui peut changer ou
   s'arrêter. NoteClaire fonctionne aussi avec une clé API ou une IA locale.
4. **Données.** Les notes de l'élève et ses particularités partent chez OpenAI : lisez
   [Vie privée](vie-privee.md).

## Les alternatives

| | Coût | Données | Remarque |
| --- | --- | --- | --- |
| Clé API OpenAI | À l'usage (budget mensuel réglable) | Envoyées à OpenAI | Conditions de l'API, pas celles de l'abonnement |
| Abonnement ChatGPT | Compris dans l'abonnement | Envoyées à OpenAI | Aperçu, connexion sur l'ordinateur hôte |
| IA locale | Gratuit | Ne sortent pas de chez vous | Qualité selon le modèle |
