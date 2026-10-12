/** Messages affichés pour chaque code d'erreur renvoyé par l'API (SPEC §30). */
const MESSAGES: Record<string, string> = {
  network_error: 'Impossible de joindre le serveur. Vérifie ta connexion.',
  not_found: "Cet élément n'existe pas ou plus.",
  empty_notes: "Tes notes sont vides : il n'y a rien à mettre au propre.",
  unknown_subject: "Cette matière n'existe pas.",
  auth_required: 'Connexion requise.',
  auth_invalid: 'Mot de passe incorrect.',
  ai_not_configured: "L'IA n'est pas configurée : il manque la clé API sur le serveur.",
  ai_timeout: "L'IA a mis trop de temps à répondre. Réessaie.",
  ai_invalid_key: "La clé API de l'IA est invalide. Il faut la corriger sur le serveur.",
  ai_quota_exceeded: 'Le crédit du compte IA est épuisé.',
  ai_rate_limited: "L'IA est très sollicitée. Réessaie dans un instant.",
  ai_unavailable: "Le service d'IA est indisponible. Réessaie plus tard.",
  ai_invalid_response: "L'IA a renvoyé une réponse inutilisable. Réessaie.",
  ai_budget_exceeded:
    'Le budget IA du mois est atteint. Les fonctions IA reviendront le mois prochain.',
  db_locked: 'La base de données est occupée. Réessaie dans un instant.',
  empty_course: 'Le cours ne peut pas être vide.',
  suggestion_not_pending: 'Cette suggestion a déjà été traitée.',
  suggestion_outdated: "Le passage visé n'existe plus dans le cours.",
  suggestion_ambiguous: 'Ce passage apparaît plusieurs fois. Choisis lequel modifier.',
  reference_unsupported: 'Formats acceptés : PDF, Markdown (.md) ou texte (.txt).',
  reference_empty: 'Le fichier est vide.',
  reference_unreadable: 'Impossible de lire ce document (PDF scanné ou protégé ?).',
  reference_too_large: 'Le fichier dépasse 30 Mo.',
  ai_local_unavailable: "Le modèle local ne répond pas. Vérifie qu'Ollama ou LM Studio est lancé.",
  ai_local_model_missing: "Le modèle local demandé n'est pas installé.",
  chatgpt_not_connected: "Connecte ton compte ChatGPT dans les Réglages pour utiliser l'IA.",
  chatgpt_reauth: 'La connexion ChatGPT a expiré : reconnecte-toi dans les Réglages.',
  chatgpt_auth_unavailable:
    'Le service de connexion ChatGPT ne répond pas. Réessaie dans un instant.',
  chatgpt_usage_limit:
    "La limite d'utilisation de ton abonnement ChatGPT pour NoteClaire est atteinte. " +
    'Tu peux la régler dans ChatGPT → Réglages → Utilisation.',
  chatgpt_not_eligible:
    "Ce compte ChatGPT ne permet pas d'utiliser l'abonnement dans d'autres applications " +
    '(offre Plus ou Pro nécessaire).',
  chatgpt_model_unavailable:
    "Ce modèle n'est pas disponible avec ton abonnement : choisis-en un autre.",
  chatgpt_storage: 'La connexion ChatGPT enregistrée est illisible : reconnecte-toi.',
  chatgpt_unavailable: 'ChatGPT ne répond pas. Réessaie dans un instant.',
  invalid_state:
    "Cette connexion a expiré ou n'a pas été lancée depuis NoteClaire. Relance-la ci-dessous.",
  access_denied: "La connexion n'a pas été terminée. Tu peux réessayer.",
  registration_incomplete: "ChatGPT n'a pas terminé l'enregistrement de l'application. Réessaie.",
  invalid_id_token: "L'identité ChatGPT n'a pas pu être vérifiée. Reconnecte-toi.",
  account_mismatch: "Ce n'est pas le même compte ChatGPT que la connexion d'origine.",
  photo_unsupported: 'Formats de photo acceptés : JPEG, PNG ou WebP.',
  photo_empty: 'La photo est vide.',
  photo_too_large: 'La photo dépasse 25 Mo.',
  photo_unreadable: 'Cette image ne peut pas être lue.',
  photo_no_text:
    'Aucun texte lisible sur cette photo. Essaie avec plus de lumière, la feuille bien à plat.',
}

const FALLBACK = "Une erreur inattendue s'est produite."

export class ApiError extends Error {
  readonly code: string
  readonly status: number
  readonly details: Record<string, unknown> | null

  constructor(
    code: string,
    status: number,
    serverMessage?: string,
    details: Record<string, unknown> | null = null,
  ) {
    super(MESSAGES[code] ?? serverMessage ?? FALLBACK)
    this.name = 'ApiError'
    this.code = code
    this.status = status
    this.details = details
  }
}

/** Message pour un code d'erreur reçu autrement que par l'API (ex. paramètre d'URL). */
export function messageForCode(code: string): string {
  return MESSAGES[code] ?? FALLBACK
}

export function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : FALLBACK
}
