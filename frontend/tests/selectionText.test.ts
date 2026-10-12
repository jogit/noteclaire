import { describe, expect, it } from 'vitest'
import { renderMarkdown } from '../src/lib/markdown'
import { selectionText } from '../src/lib/selectionText'

function selectAll(markdown: string): Range {
  const root = document.createElement('div')
  root.innerHTML = renderMarkdown(markdown)
  document.body.append(root)
  const range = document.createRange()
  range.selectNodeContents(root)
  return range
}

describe('selectionText', () => {
  it('remet chaque formule en LaTeX, sans la copie cachée de KaTeX', () => {
    const text = selectionText(selectAll('Elle s’exprime en $\\mathrm{g \\cdot L^{-1}}$ ici.'))
    expect(text).toBe('Elle s’exprime en $\\mathrm{g \\cdot L^{-1}}$ ici.')
  })

  it('sépare les paragraphes par un saut de ligne', () => {
    expect(selectionText(selectAll('Premier.\n\nSecond.'))).toBe('Premier.\nSecond.')
  })
})
