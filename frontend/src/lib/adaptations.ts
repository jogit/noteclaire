import { api } from '../api/client'
import type { Adaptation } from '../api/types'

let cached: Promise<Adaptation[]> | undefined

/** Liste des particularités, demandée une seule fois pour toute l'application. */
export function loadAdaptations(): Promise<Adaptation[]> {
  cached ??= api.adaptations().catch((error) => {
    cached = undefined // on réessaiera la prochaine fois
    throw error
  })
  return cached
}
