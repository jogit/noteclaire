import type { Component } from 'vue'
import {
  BookOpen,
  Calculator,
  Cpu,
  FlaskConical,
  GraduationCap,
  Landmark,
  Languages,
  Leaf,
  MessagesSquare,
  Scale,
  TrendingUp,
} from 'lucide-vue-next'

/**
 * Présentation des matières (couleur, icône). La liste des matières elle-même vient
 * de l'API (backend/app/subjects.py) : une matière inconnue ici reçoit un style par défaut.
 */
const STYLES: Record<string, { color: string; icon: Component }> = {
  mathematiques: { color: '#4f6fe0', icon: Calculator },
  francais: { color: '#d4508a', icon: BookOpen },
  'histoire-geographie': { color: '#c98a1e', icon: Landmark },
  ses: { color: '#16958a', icon: TrendingUp },
  'physique-chimie': { color: '#8a5ad8', icon: FlaskConical },
  svt: { color: '#3c9a48', icon: Leaf },
  anglais: { color: '#d9534f', icon: Languages },
  espagnol: { color: '#e07a2e', icon: MessagesSquare },
  allemand: { color: '#b0912a', icon: Languages },
  snt: { color: '#1f8fbf', icon: Cpu },
  emc: { color: '#5c64c9', icon: Scale },
}

const DEFAULT = { color: '#6b72a8', icon: GraduationCap }

export function subjectStyle(slug: string | undefined) {
  return (slug && STYLES[slug]) || DEFAULT
}

/** Variable CSS --subject utilisée par les pastilles, cartes et bandeaux. */
export function subjectVars(slug: string | undefined): Record<string, string> {
  return { '--subject': subjectStyle(slug).color }
}
