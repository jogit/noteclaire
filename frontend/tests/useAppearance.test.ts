import { nextTick } from 'vue'
import { describe, expect, it } from 'vitest'
import { useAppearance } from '../src/composables/useAppearance'

describe('useAppearance', () => {
  it('applique et mémorise la taille du texte, le thème et l’espacement', async () => {
    const { size, theme, spacing } = useAppearance()
    expect(document.documentElement.dataset.spacing).toBe('normal')
    expect(document.documentElement.style.getPropertyValue('--text-scale')).toBe('1')
    expect(document.documentElement.dataset.theme).toBe('auto')

    size.value = 'xlarge'
    theme.value = 'cream'
    spacing.value = 'large'
    await nextTick()

    expect(document.documentElement.style.getPropertyValue('--text-scale')).toBe('1.3')
    expect(document.documentElement.dataset.theme).toBe('cream')
    expect(document.documentElement.dataset.spacing).toBe('large')
    expect(localStorage.getItem('noteclaire:text-size')).toBe('xlarge')
    expect(localStorage.getItem('noteclaire:theme')).toBe('cream')
    expect(localStorage.getItem('noteclaire:spacing')).toBe('large')
  })
})
