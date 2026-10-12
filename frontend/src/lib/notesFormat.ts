/**
 * Format des notes : du texte simple, ligne par ligne, avec deux repères :
 * - « [?lecture|autre lecture|…] » : passage incertain lu sur une photo
 *   (« [?|a|b] » sans lecture retenue ; « [illisible] » sans aucune proposition) ;
 * - « ![légende](/api/images/…) » seul sur sa ligne : image (schéma…).
 */
import type { JSONContent } from '@tiptap/core'

export interface UncertainSpot {
  guess: string
  options: string[]
}

const SPOT_PATTERN = /\[\?([^\]\n]*)\]|\[illisible\]/gi
const IMAGE_LINE = /^!\[([^\]\n]*)\]\((\/api\/images\/[^)\s]+)\)\s*$/

/** Repère texte d'un passage incertain. */
export function spotMarker({ guess, options }: UncertainSpot): string {
  const clean = (value: string) => value.replace(/[|\]\n]/g, ' ').trim()
  const others = options.map(clean).filter((o) => o && o !== clean(guess))
  if (!clean(guess) && !others.length) return '[illisible]'
  return `[?${[clean(guess), ...others].join('|')}]`
}

export function parseSpot(marker: string): UncertainSpot {
  if (/^\[illisible\]$/i.test(marker)) return { guess: '', options: [] }
  const [guess = '', ...options] = marker.slice(2, -1).split('|')
  return { guess: guess.trim(), options: options.map((o) => o.trim()).filter(Boolean) }
}

const SCHEMA_MARKER = /\[sch[ée]ma\s*:\s*([^\]\n]+)\]/gi

/**
 * Remplace par leur image les « [schéma : …] » que l'IA a su découper sur la photo
 * (`figures[i].index` = rang du repère). Une image est toujours seule sur sa ligne.
 */
export function insertFigures(text: string, figures: { index: number; url: string }[]): string {
  const urls = new Map(figures.map((f) => [f.index, f.url]))
  let rank = 0
  return text.replace(
    SCHEMA_MARKER,
    (marker, description: string, offset: number, whole: string) => {
      const url = urls.get(rank++)
      if (!url) return marker
      const before = offset === 0 || whole[offset - 1] === '\n' ? '' : '\n'
      const end = offset + marker.length
      const after = end >= whole.length || whole[end] === '\n' ? '' : '\n'
      return `${before}![${description.trim().replace(/[\][]/g, '')}](${url})${after}`
    },
  )
}

/** Texte lu sur une photo (« [?] » + liste « uncertain ») → texte de notes avec repères. */
export function photoTextToNotes(text: string, uncertain: UncertainSpot[]): string {
  let index = 0
  return text.replace(/\[\?\]/g, () => spotMarker(uncertain[index++] ?? { guess: '', options: [] }))
}

function inlineContent(line: string): JSONContent[] {
  const content: JSONContent[] = []
  let last = 0
  for (const match of line.matchAll(SPOT_PATTERN)) {
    if (match.index > last) content.push({ type: 'text', text: line.slice(last, match.index) })
    content.push({ type: 'uncertain', attrs: parseSpot(match[0]) })
    last = match.index + match[0].length
  }
  if (last < line.length) content.push({ type: 'text', text: line.slice(last) })
  return content
}

/** Notes (texte) → document de l'éditeur. */
export function notesToDoc(notes: string): JSONContent {
  const lines = notes.replace(/\r\n/g, '\n').split('\n')
  return {
    type: 'doc',
    content: lines.map((line) => {
      const image = IMAGE_LINE.exec(line)
      if (image) return { type: 'image', attrs: { alt: image[1], src: image[2] } }
      const content = inlineContent(line)
      return content.length ? { type: 'paragraph', content } : { type: 'paragraph' }
    }),
  }
}

/** Document de l'éditeur → notes (texte). */
export function docToNotes(doc: JSONContent): string {
  return (doc.content ?? [])
    .map((block) => {
      if (block.type === 'image') return `![${block.attrs?.alt ?? ''}](${block.attrs?.src ?? ''})`
      return (block.content ?? [])
        .map((node) => {
          if (node.type === 'uncertain') return spotMarker(node.attrs as UncertainSpot)
          if (node.type === 'hardBreak') return '\n'
          return node.text ?? ''
        })
        .join('')
    })
    .join('\n')
}

/** Nombre de passages encore à vérifier dans des notes. */
export function countSpots(notes: string): number {
  return [...notes.matchAll(SPOT_PATTERN)].length
}
