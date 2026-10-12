import { ref, watch } from 'vue'

/** Apparence (SPEC §35) : thème, taille du texte et espacement, mémorisés dans le navigateur. */
export const TEXT_SIZES = {
  // Multiplie la taille de base, qui suit la largeur de l'écran (voir styles.css).
  normal: { label: 'Normal', scale: 1 },
  large: { label: 'Grand', scale: 1.15 },
  xlarge: { label: 'Très grand', scale: 1.3 },
} as const

export const THEMES = {
  auto: 'Comme l’appareil',
  light: 'Clair',
  cream: 'Crème (fond doux)',
  dark: 'Sombre',
} as const

export const SPACINGS = {
  normal: 'Normal',
  large: 'Aéré (lettres et mots plus espacés)',
} as const

type TextSize = keyof typeof TEXT_SIZES
type Theme = keyof typeof THEMES
type Spacing = keyof typeof SPACINGS

function read<T extends string>(key: string, allowed: Record<T, unknown>, fallback: T): T {
  try {
    const value = localStorage.getItem(key)
    if (value && value in allowed) return value as T
  } catch {
    // stockage indisponible (navigation privée…) : valeur par défaut
  }
  return fallback
}

function write(key: string, value: string): void {
  try {
    localStorage.setItem(key, value)
  } catch {
    // sans conséquence
  }
}

const size = ref<TextSize>(read('noteclaire:text-size', TEXT_SIZES, 'normal'))
const theme = ref<Theme>(read('noteclaire:theme', THEMES, 'auto'))
const spacing = ref<Spacing>(read('noteclaire:spacing', SPACINGS, 'normal'))

watch(
  size,
  (value) => {
    document.documentElement.style.setProperty('--text-scale', String(TEXT_SIZES[value].scale))
    write('noteclaire:text-size', value)
  },
  { immediate: true },
)

watch(
  theme,
  (value) => {
    document.documentElement.dataset.theme = value
    write('noteclaire:theme', value)
  },
  { immediate: true },
)

watch(
  spacing,
  (value) => {
    document.documentElement.dataset.spacing = value
    write('noteclaire:spacing', value)
  },
  { immediate: true },
)

export function useAppearance() {
  return { size, theme, spacing }
}
