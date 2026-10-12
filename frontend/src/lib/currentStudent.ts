const KEY = 'noteclaire:student'

/**
 * Élève choisi dans ce navigateur. Il est envoyé au serveur dans l'en-tête X-Student-Id, et dans
 * un cookie pour les images et téléchargements que le navigateur demande sans passer par le code.
 */
export function getStudentId(): number | undefined {
  try {
    const value = Number(localStorage.getItem(KEY))
    return Number.isInteger(value) && value > 0 ? value : undefined
  } catch {
    return undefined
  }
}

function writeCookie(id: number): void {
  document.cookie = `noteclaire_student=${id}; path=/; max-age=31536000; samesite=strict`
}

/** Au démarrage : le cookie suit le choix déjà mémorisé (navigateur ouvert avant le cookie). */
export function syncStudentCookie(): void {
  const id = getStudentId()
  if (id !== undefined) writeCookie(id)
}

export function setStudentId(id: number): void {
  writeCookie(id)
  try {
    localStorage.setItem(KEY, String(id))
  } catch {
    // stockage indisponible : le serveur utilise alors le premier élève
  }
}
