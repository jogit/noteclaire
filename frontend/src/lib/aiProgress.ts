/**
 * Progression estimée des appels IA. L'IA ne dit pas où elle en est : on s'appuie sur la
 * durée habituelle de l'opération (médiane des derniers appels, voir /api/usage/durations).
 *
 * La barre atteint 90 % à la durée habituelle, puis ralentit sans jamais dépasser 98 % :
 * elle n'annonce jamais « fini » avant la réponse.
 */
import { api } from '../api/client'

export type AiOperation =
  'structure' | 'analyze' | 'revision_sheet' | 'quiz' | 'explain' | 'photo' | 'redraw'

const FALLBACK: Record<AiOperation, number> = {
  structure: 20,
  analyze: 30,
  revision_sheet: 25,
  quiz: 20,
  explain: 10,
  photo: 15,
  redraw: 25,
}

/** Étapes affichées sous la barre, réparties sur la durée estimée. */
export const STAGES: Record<AiOperation, string[]> = {
  structure: [
    'Lecture de tes notes',
    'Organisation en parties',
    'Mise en forme : encadrés, formules, couleurs',
    'Dernières vérifications',
  ],
  analyze: [
    'Lecture du cours',
    'Comparaison avec le programme officiel',
    'Recherche des erreurs probables',
    'Rédaction des remarques',
  ],
  revision_sheet: [
    'Lecture du cours',
    "Choix de l'essentiel",
    'Mise en page de la fiche',
    'Dernières vérifications',
  ],
  quiz: [
    'Lecture du cours',
    'Choix des notions à tester',
    'Rédaction des questions',
    'Vérification des réponses',
  ],
  explain: ['Lecture du passage', 'Recherche d’une explication simple', 'Rédaction'],
  redraw: [
    'Envoi du schéma',
    'Lecture des textes et des flèches',
    'Dessin du schéma propre',
    'Vérification',
  ],
  photo: [
    'Envoi de la photo',
    "Lecture de l'écriture",
    'Repérage des mots difficiles',
    'Mise en forme du texte',
  ],
}

const START_CURVE = 2.3 // 1 - e^-2.3 ≈ 90 %

export function estimatedProgress(elapsedSeconds: number, expectedSeconds: number): number {
  const expected = Math.max(1, expectedSeconds)
  if (elapsedSeconds <= 0) return 0
  if (elapsedSeconds <= expected) {
    return (
      (0.9 * (1 - Math.exp((-START_CURVE * elapsedSeconds) / expected))) /
      (1 - Math.exp(-START_CURVE))
    )
  }
  const late = (elapsedSeconds - expected) / expected
  return 0.9 + 0.08 * (1 - Math.exp(-late))
}

/** Les premières étapes se partagent le début ; la dernière commence à 85 %. */
export function stageIndex(progress: number, stageCount: number): number {
  if (progress >= 0.85) return stageCount - 1
  return Math.min(stageCount - 2, Math.floor((progress / 0.85) * (stageCount - 1)))
}

let durations: Promise<Partial<Record<AiOperation, number>>> | undefined

/** Durées habituelles, chargées une fois puis rafraîchies après chaque appel terminé. */
export async function expectedSeconds(operation: AiOperation): Promise<number> {
  durations ??= Promise.resolve()
    .then(() => api.aiDurations())
    .catch(() => ({}))
  return (await durations)[operation] ?? FALLBACK[operation]
}

export function refreshDurations(): void {
  durations = undefined
}
