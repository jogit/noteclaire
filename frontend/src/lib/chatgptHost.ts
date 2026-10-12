/**
 * OpenAI ne renvoie, pour la connexion ChatGPT, que vers http://127.0.0.1:<port>/auth/callback (pas
 * `localhost`) : ce retour atteint la machine du navigateur. La connexion se fait donc une fois,
 * depuis l'ordinateur qui héberge NoteClaire, ouvert à l'adresse 127.0.0.1.
 */
export const CHATGPT_USAGE_URL = 'https://chatgpt.com/settings/usage'

export function canSignInHere(hostname = window.location.hostname): boolean {
  return ['127.0.0.1', '[::1]', '::1'].includes(hostname)
}
