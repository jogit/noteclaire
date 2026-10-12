import { Editor } from '@tiptap/core'
import { describe, expect, it } from 'vitest'
import { courseEditorExtensions, courseMarkdown } from '../src/lib/courseEditor'

function roundTrip(markdown: string): string {
  const editor = new Editor({
    extensions: courseEditorExtensions(),
    content: markdown,
    contentType: 'markdown',
  })
  const result = courseMarkdown(editor)
  editor.destroy()
  return result
}

const COURSE = `# Espèces chimiques

::: definition Espèce chimique
Une ==espèce chimique== est représentée par une **formule chimique**.
:::

::: exemple
- $\\mathrm{Fe}$ : fer ;
- $\\mathrm{H_2O}$ : eau.
:::

## Formules

$$\\frac{m}{V}$$

| Type | Exemples |
| --- | --- |
| Homogène | Sirop |

![Schéma de la cellule](/api/images/3/abc.jpg)

\`\`\`mermaid
mindmap
  root((Chimie))
    Corps pur
\`\`\`

Texte avec [schéma : la cellule] à ajouter.`

describe('éditeur visuel — aller-retour Markdown', () => {
  it('conserve tous les éléments du cours', () => {
    const result = roundTrip(COURSE)
    expect(result).toContain('# Espèces chimiques')
    expect(result).toContain('::: definition Espèce chimique')
    expect(result).toContain(
      'Une ==espèce chimique== est représentée par une **formule chimique**.',
    )
    expect(result).toContain('::: exemple')
    expect(result).toContain('$\\mathrm{Fe}$ : fer ;')
    expect(result).toContain('$$\\frac{m}{V}$$')
    expect(result).toContain('| Homogène | Sirop')
    expect(result).toContain('![Schéma de la cellule](/api/images/3/abc.jpg)')
    expect(result).toContain('```mermaid\nmindmap\n  root((Chimie))\n    Corps pur\n```')
    expect(result).toContain('[schéma : la cellule]')
  })

  it('ne prend pas « Ex. : » pour une liste, mais garde les listes numérotées', () => {
    expect(roundTrip("::: exemple\nEx. : diamant, lingot d'or.\n:::")).toBe(
      "::: exemple\nEx. : diamant, lingot d'or.\n:::",
    )
    expect(roundTrip('1. Placer A\n2. Tracer AB')).toBe('1. Placer A\n2. Tracer AB')
  })

  it('ne laisse pas de crochets échappés hors des formules', () => {
    expect(roundTrip('Un corps pur [illisible] et $\\left[0;1\\right]$.')).toBe(
      'Un corps pur [illisible] et $\\left[0;1\\right]$.',
    )
  })

  it('est stable : un second aller-retour ne change plus rien', () => {
    const once = roundTrip(COURSE)
    expect(roundTrip(once)).toBe(once)
  })
})
