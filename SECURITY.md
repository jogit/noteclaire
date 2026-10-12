# Sécurité

## Signaler une faille

Merci de **ne pas** ouvrir d'issue publique pour une faille de sécurité. Utilisez le signalement
privé de GitHub : onglet **Security** du dépôt → **Report a vulnerability**. Décrivez ce que vous
avez observé, comment le reproduire et la version de NoteClaire concernée.

Vous recevrez un accusé de réception sous quelques jours. NoteClaire est un projet personnel maintenu
sur le temps de son auteur : pas de délai garanti, mais les failles sont traitées en priorité.

## Versions prises en charge

Seule la dernière version publiée reçoit des correctifs.

## Ce que NoteClaire protège (et ce qu'il ne protège pas)

- L'accès est protégé par un mot de passe commun à la famille ; chaque élève n'accède qu'à ses
  chapitres côté serveur, mais changer d'élève dans le navigateur reste libre.
- Les clés et jetons sont chiffrés au repos dans `data/secrets/`, avec une clé rangée à côté : cela
  protège des fuites accidentelles (copie de la base, sauvegarde), pas d'une personne qui contrôle
  déjà la machine.
- NoteClaire est pensé pour un réseau domestique ou une machine personnelle. Pour l'exposer sur
  Internet, placez-le derrière HTTPS (votre propre reverse proxy) et gardez
  `APP_PASSWORD` fort.
