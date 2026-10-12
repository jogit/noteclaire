import katexPluginModule from '@vscode/markdown-it-katex'
import katex from 'katex'
import MarkdownIt from 'markdown-it'
import containerPlugin from 'markdown-it-container'
import markPlugin from 'markdown-it-mark'
import 'katex/dist/katex.min.css'

// Le paquet est publié en CommonJS (exports.default) : selon l'outil, l'import par défaut
// renvoie la fonction ou le module.
const katexPlugin =
  (katexPluginModule as unknown as { default?: typeof katexPluginModule }).default ??
  katexPluginModule

/**
 * Encadrés du cours : ::: definition [titre facultatif] … :::
 * Le libellé est toujours écrit en toutes lettres : l'information ne passe pas que par la couleur.
 */
export const CALLOUTS = {
  definition: 'Définition',
  propriete: 'Propriété',
  exemple: 'Exemple',
  methode: 'Méthode',
  attention: 'Attention',
  retenir: 'À retenir',
} as const

export type CalloutType = keyof typeof CALLOUTS

/** Images autorisées : uniquement celles hébergées par NoteClaire (pas de pixel externe). */
const IMAGE_PREFIX = '/api/images/'

const SCHEMA_PATTERN = /\[sch[ée]ma\s*:\s*([^\]\n]+)\]/gi

// html: false — le Markdown vient de l'IA : aucun HTML brut n'est interprété.
const md = new MarkdownIt({ html: false, linkify: true, breaks: false })
// Même version de KaTeX que la feuille de style importée ci-dessus : sinon les accents
// (flèche de \vec, chapeau…) sont mal placés.
// Les types du plugin décrivent KaTeX 0.16 : seule la liste des avertissements diffère.
md.use(katexPlugin, { throwOnError: false, katex: katex as never })
md.use(markPlugin)

for (const [type, label] of Object.entries(CALLOUTS)) {
  md.use(containerPlugin, type, {
    validate: (params: string) => new RegExp(`^${type}(\\s+.*)?$`).test(params.trim()),
    render: (tokens: { info: string; nesting: number }[], index: number) => {
      const token = tokens[index]!
      if (token.nesting !== 1) return '</aside>\n'
      const title = token.info.trim().slice(type.length).trim()
      return (
        `<aside class="callout callout-${type}"><p class="callout-title">` +
        `<span class="callout-label">${label}</span>` +
        (title ? ` ${md.utils.escapeHtml(title)}` : '') +
        '</p>\n'
      )
    },
  })
}

// Emplacement d'un schéma relevé sur la photo des notes : ::: schema <n> <description>
md.use(containerPlugin, 'schema', {
  validate: (params: string) => /^schema\s+\d+/.test(params.trim()),
  render: (tokens: { info: string; nesting: number }[], index: number) => {
    const token = tokens[index]!
    if (token.nesting !== 1) return '</div>\n'
    const [, number, description] = token.info.trim().match(/^schema\s+(\d+)\s*(.*)$/) ?? []
    return (
      `<div class="schema-placeholder" data-schema-index="${number}">` +
      `<p><strong>Schéma à ajouter :</strong> ${md.utils.escapeHtml(description ?? '')}</p>` +
      `<button type="button" class="secondary" data-action="add-schema-image" ` +
      `data-schema-index="${number}">Ajouter la photo du schéma</button>`
    )
  },
})

// Schémas Mermaid (carte mentale, frise, diagramme) : dessinés après l'affichage.
const defaultFence = md.renderer.rules.fence!
md.renderer.rules.fence = (tokens, index, options, env, self) => {
  const token = tokens[index]!
  if (token.info.trim() === 'mermaid') {
    const source = md.utils.escapeHtml(token.content)
    return `<figure class="diagram" data-diagram><pre class="diagram-source">${source}</pre></figure>\n`
  }
  return defaultFence(tokens, index, options, env, self)
}

const defaultImage = md.renderer.rules.image!
md.renderer.rules.image = (tokens, index, options, env, self) => {
  const token = tokens[index]!
  const src = String(token.attrGet('src') ?? '')
  if (!src.startsWith(IMAGE_PREFIX)) {
    return `<span class="image-blocked">[image : ${md.utils.escapeHtml(token.content)}]</span>`
  }
  token.attrSet('loading', 'lazy')
  return defaultImage(tokens, index, options, env, self)
}

/** Remplace chaque [schéma : …] par un emplacement numéroté (bloc à part). */
function withSchemaPlaceholders(source: string): string {
  let count = 0
  return source.replace(SCHEMA_PATTERN, (_, description: string) => {
    const block = `\n\n::: schema ${count} ${description.trim()}\n:::\n\n`
    count++
    return block
  })
}

/** Remplace le n-ième [schéma : …] du Markdown par une image. */
export function replaceSchema(source: string, index: number, imageUrl: string): string {
  let count = 0
  return source.replace(SCHEMA_PATTERN, (match, description: string) =>
    count++ === index ? `![${description.trim()}](${imageUrl})` : match,
  )
}

/** L'IA glisse parfois des « <br> » (retour à la ligne HTML), que le rendu refuse : un espace. */
const LINE_BREAK_TAG = /<br\s*\/?>/gi

export function renderMarkdown(source: string): string {
  return md.render(withSchemaPlaceholders(source.replace(LINE_BREAK_TAG, ' ')))
}

/** Rendu sur une ligne (sans paragraphe), pour citer un court passage du cours. */
export function renderInlineMarkdown(source: string): string {
  return md.renderInline(source.replace(LINE_BREAK_TAG, ' '))
}

const MATH_SEGMENT = /(\$\$[\s\S]*?\$\$|\$[^$\n]*\$)/

/**
 * Début d'un passage Markdown sur une ligne, coupé vers `max` caractères sans couper
 * une formule ni un mot.
 */
export function markdownExcerpt(source: string, max = 100): string {
  const flat = source
    .split('\n')
    .map((line) =>
      line
        .replace(/^\s*:::.*$/, '')
        .replace(/^\s*#{1,6}\s+/, '')
        .replace(/^\s*>\s?/, '')
        .replace(/^\s*(?:[-*+]|\d+[.)])\s+/, '')
        .trim(),
    )
    .filter(Boolean)
    .join(' ')
  let result = ''
  for (const segment of flat.split(MATH_SEGMENT)) {
    if (!segment) continue
    if (result.length + segment.length <= max) {
      result += segment
      continue
    }
    if (!MATH_SEGMENT.test(segment)) {
      const room = segment.slice(0, max - result.length)
      const cut = room.lastIndexOf(' ')
      result += cut > 0 ? room.slice(0, cut) : ''
    }
    return `${result.trimEnd()}…`
  }
  return result
}
