import { describe, expect, it } from 'vitest'
import { anchorSuggestions, anchorText, clearAnchors } from '../src/lib/suggestionAnchors'
import { renderMarkdown } from '../src/lib/markdown'

function render(markdown: string): HTMLElement {
  const root = document.createElement('div')
  root.innerHTML = renderMarkdown(markdown)
  return root
}

describe('anchorText', () => {
  it('retire la mise en forme Markdown', () => {
    expect(anchorText('- **Définition** : la ==pente== est _a_')).toBe(
      'Définition : la pente est a',
    )
    expect(anchorText('## Les vecteurs')).toBe('Les vecteurs')
  })

  it('garde le plus long morceau de texte autour d’une formule', () => {
    expect(anchorText('La pente $a = \\frac{y_B - y_A}{x_B - x_A}$ se calcule ainsi')).toBe(
      'se calcule ainsi',
    )
    expect(anchorText('$x$')).toBe('')
  })
})

describe('anchorSuggestions', () => {
  it('surligne un passage réparti sur plusieurs balises', () => {
    const root = render('Un vecteur est défini par **une direction**, un sens et une norme.')
    const found = anchorSuggestions(root, [
      { id: 1, original_text: 'défini par **une direction**, un sens' },
    ])
    expect(found).toEqual(new Set([1]))
    const marks = root.querySelectorAll('mark.suggestion-anchor')
    expect([...marks].map((m) => m.textContent).join('')).toBe('défini par une direction, un sens')
    expect(root.textContent).toBe(
      'Un vecteur est défini par une direction, un sens et une norme.\n',
    )
  })

  it('ignore ce qui n’est pas dans le cours et nettoie les anciens surlignages', () => {
    const root = render('Texte du cours')
    anchorSuggestions(root, [{ id: 1, original_text: 'Texte' }])
    expect(anchorSuggestions(root, [{ id: 2, original_text: 'absent' }])).toEqual(new Set())
    expect(root.querySelector('mark')).toBeNull()
    clearAnchors(root)
    expect(root.textContent).toBe('Texte du cours\n')
  })
})
