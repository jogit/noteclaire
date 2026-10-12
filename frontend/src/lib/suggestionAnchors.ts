/**
 * Repère dans le cours affiché le passage visé par chaque suggestion, pour le surligner.
 *
 * Les suggestions citent le Markdown du cours ; on cherche le texte lisible correspondant
 * (sans les marques de mise en forme). Une formule ou un schéma ne peut pas être retrouvé
 * tel quel : on garde alors le plus long morceau de texte ordinaire du passage.
 */

export const ANCHOR_CLASS = 'suggestion-anchor'

const SKIPPED = '.katex, .diagram, .schema-placeholder, mark.' + ANCHOR_CLASS

/** Plus long morceau de texte lisible du passage (au moins 4 caractères), ou ''. */
export function anchorText(markdown: string): string {
  const segments = markdown
    .replace(/\$\$[\s\S]*?\$\$|\$[^$\n]*\$/g, '\n') // formules
    .replace(/!\[[^\]]*\]\([^)]*\)/g, '\n') // images
    .replace(/\[([^\]]*)\]\([^)]*\)/g, '$1') // liens : on garde le texte
    .split('\n')
    .map((line) =>
      line
        .replace(/^\s*:::.*$/, '')
        .replace(/^\s*#{1,6}\s+/, '')
        .replace(/^\s*>\s?/, '')
        .replace(/^\s*(?:[-*+]|\d+[.)])\s+/, '')
        .replace(/\*\*|__|==|~~|`/g, '')
        .replace(/(^|[^\w])[*_](?=\S)|(?<=\S)[*_](?=[^\w]|$)/g, '$1')
        .replace(/\|/g, ' ')
        .replace(/\s+/g, ' ')
        .trim(),
    )
  const longest = segments.reduce((best, s) => (s.length > best.length ? s : best), '')
  return longest.length >= 4 ? longest : ''
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function textNodes(root: HTMLElement): Text[] {
  const nodes: Text[] = []
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode: (node) =>
      node.parentElement?.closest(SKIPPED) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT,
  })
  for (let node = walker.nextNode(); node; node = walker.nextNode()) nodes.push(node as Text)
  return nodes
}

/** Entoure de <mark> la plage [start, end[ du texte concaténé des nœuds. */
function wrapRange(nodes: Text[], start: number, end: number, id: number): HTMLElement[] {
  const marks: HTMLElement[] = []
  let offset = 0
  for (const node of nodes) {
    const length = node.data.length
    const from = Math.max(start, offset)
    const to = Math.min(end, offset + length)
    if (from < to && node.data.slice(from - offset, to - offset).trim()) {
      let target = node
      if (from > offset) target = target.splitText(from - offset)
      if (to < offset + length) target.splitText(to - from)
      const mark = document.createElement('mark')
      mark.className = ANCHOR_CLASS
      mark.dataset.suggestionId = String(id)
      target.parentNode!.insertBefore(mark, target)
      mark.appendChild(target)
      marks.push(mark)
    }
    offset += length
  }
  return marks
}

/** Retire les surlignages posés précédemment. */
export function clearAnchors(root: HTMLElement): void {
  for (const mark of root.querySelectorAll<HTMLElement>(`mark.${ANCHOR_CLASS}`)) {
    mark.replaceWith(...mark.childNodes)
  }
  root.normalize()
}

/**
 * Surligne le passage de chaque suggestion (première occurrence) et renvoie les identifiants
 * des suggestions retrouvées dans le cours.
 */
export function anchorSuggestions(
  root: HTMLElement,
  suggestions: { id: number; original_text: string }[],
): Set<number> {
  clearAnchors(root)
  const found = new Set<number>()
  for (const suggestion of suggestions) {
    const anchor = anchorText(suggestion.original_text)
    if (!anchor) continue
    const nodes = textNodes(root)
    const text = nodes.map((n) => n.data).join('')
    const pattern = new RegExp(escapeRegExp(anchor).replace(/ /g, '\\s+'))
    const match = pattern.exec(text)
    if (!match) continue
    if (wrapRange(nodes, match.index, match.index + match[0].length, suggestion.id).length) {
      found.add(suggestion.id)
    }
  }
  return found
}
