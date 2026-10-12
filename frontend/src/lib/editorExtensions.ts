/**
 * Éléments sur mesure de l'éditeur visuel (TipTap), avec leur conversion Markdown :
 * le cours reste stocké dans le même Markdown que celui produit par la mise au propre.
 */
import { mergeAttributes, Node, type MarkdownToken } from '@tiptap/core'
import type { Transaction } from '@tiptap/pm/state'
import katex from 'katex'
import { renderDiagrams } from './diagrams'
import { CALLOUTS, type CalloutType } from './markdown'

const CALLOUT_TYPES = Object.keys(CALLOUTS) as CalloutType[]
const CALLOUT_OPEN = new RegExp(`^:::[ \\t]*(${CALLOUT_TYPES.join('|')})\\b`, 'm')
const CALLOUT_BLOCK = new RegExp(
  `^:::[ \\t]*(${CALLOUT_TYPES.join('|')})(?:[ \\t]+([^\\n]*))?\\n([\\s\\S]*?)\\n:::[ \\t]*(?:\\n|$)`,
)

/** Encadré : ::: definition Titre facultatif … ::: */
export const Callout = Node.create({
  name: 'callout',
  group: 'block',
  content: 'block+',
  defining: true,

  addAttributes() {
    return { type: { default: 'definition' }, title: { default: '' } }
  },

  parseHTML() {
    return [
      {
        tag: 'aside[data-callout]',
        getAttrs: (element: HTMLElement) => ({
          type: element.getAttribute('data-callout'),
          title: element.getAttribute('data-title') ?? '',
        }),
      },
    ]
  },

  renderHTML({ node, HTMLAttributes }) {
    const type = node.attrs.type as CalloutType
    return [
      'aside',
      mergeAttributes(HTMLAttributes, {
        'data-callout': type,
        'data-title': node.attrs.title,
        class: `callout callout-${type}`,
      }),
      [
        'p',
        { class: 'callout-title', contenteditable: 'false' },
        ['span', { class: 'callout-label' }, CALLOUTS[type] ?? type],
        node.attrs.title ? ` ${node.attrs.title}` : '',
      ],
      ['div', { class: 'callout-body' }, 0],
    ]
  },

  markdownTokenizer: {
    name: 'callout',
    level: 'block',
    start: (src: string) => src.search(CALLOUT_OPEN),
    tokenize(src, _tokens, lexer) {
      const match = CALLOUT_BLOCK.exec(src)
      if (!match) return undefined
      return {
        type: 'callout',
        raw: match[0],
        calloutType: match[1],
        title: (match[2] ?? '').trim(),
        tokens: lexer.blockTokens(match[3] ?? ''),
      }
    },
  },

  parseMarkdown(token: MarkdownToken, helpers) {
    return helpers.createNode(
      'callout',
      { type: token.calloutType, title: token.title ?? '' },
      helpers.parseChildren(token.tokens ?? []),
    )
  },

  renderMarkdown(node, helpers) {
    const title = node.attrs?.title ? ` ${node.attrs.title}` : ''
    const body = helpers.renderChildren(node.content ?? [], '\n\n').trim()
    return `::: ${node.attrs?.type}${title}\n${body}\n:::`
  },
})

function katexElement(tag: 'span' | 'div', latex: string, displayMode: boolean): HTMLElement {
  const element = document.createElement(tag)
  element.className = displayMode ? 'math-node math-block' : 'math-node'
  element.contentEditable = 'false'
  element.title = 'Cliquer pour modifier la formule'
  element.innerHTML = katex.renderToString(latex || '\\square', {
    throwOnError: false,
    displayMode,
  })
  return element
}

function mathNodeView(displayMode: boolean) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return ({ node, getPos, editor }: any) => {
    const dom = katexElement(displayMode ? 'div' : 'span', node.attrs.latex, displayMode)
    dom.addEventListener('click', () => {
      const latex = window.prompt(
        'Formule (notation LaTeX, ex. x^2 ou \\frac{1}{2}) :',
        node.attrs.latex,
      )
      if (latex === null || typeof getPos !== 'function') return
      editor
        .chain()
        .focus()
        .command(({ tr }: { tr: Transaction }) => {
          tr.setNodeMarkup(getPos(), undefined, { latex })
          return true
        })
        .run()
    })
    return { dom }
  }
}

/** Formule dans le texte : $…$ */
export const MathInline = Node.create({
  name: 'mathInline',
  group: 'inline',
  inline: true,
  atom: true,

  addAttributes() {
    return { latex: { default: '' } }
  },

  parseHTML() {
    return [{ tag: 'span[data-math]', getAttrs: (el: HTMLElement) => ({ latex: el.dataset.math }) }]
  },

  renderHTML({ node }) {
    return ['span', { 'data-math': node.attrs.latex }, `$${node.attrs.latex}$`]
  },

  addNodeView() {
    return mathNodeView(false)
  },

  markdownTokenizer: {
    name: 'mathInline',
    level: 'inline',
    start: (src: string) => src.indexOf('$'),
    tokenize(src: string) {
      const match = /^\$(?!\$)((?:\\\$|[^$\n])+?)\$(?!\$)/.exec(src)
      if (!match) return undefined
      return { type: 'mathInline', raw: match[0], latex: match[1] }
    },
  },

  parseMarkdown(token: MarkdownToken, helpers) {
    return helpers.createNode('mathInline', { latex: token.latex })
  },

  renderMarkdown(node) {
    return `$${node.attrs?.latex ?? ''}$`
  },
})

/** Formule centrée : $$ … $$ */
export const MathBlock = Node.create({
  name: 'mathBlock',
  group: 'block',
  atom: true,

  addAttributes() {
    return { latex: { default: '' } }
  },

  parseHTML() {
    return [{ tag: 'div[data-math]', getAttrs: (el: HTMLElement) => ({ latex: el.dataset.math }) }]
  },

  renderHTML({ node }) {
    return ['div', { 'data-math': node.attrs.latex }, `$$${node.attrs.latex}$$`]
  },

  addNodeView() {
    return mathNodeView(true)
  },

  markdownTokenizer: {
    name: 'mathBlock',
    level: 'block',
    start: (src: string) => src.search(/^\$\$/m),
    tokenize(src: string) {
      const match = /^\$\$[ \t]*\n?([\s\S]+?)\n?[ \t]*\$\$[ \t]*(?:\n|$)/.exec(src)
      if (!match) return undefined
      return { type: 'mathBlock', raw: match[0], latex: (match[1] ?? '').trim() }
    },
  },

  parseMarkdown(token: MarkdownToken, helpers) {
    return helpers.createNode('mathBlock', { latex: token.latex })
  },

  renderMarkdown(node) {
    return `$$${node.attrs?.latex ?? ''}$$`
  },
})

/** Schéma Mermaid (carte mentale, frise…) : dessiné, son code est conservé tel quel. */
export const Diagram = Node.create({
  name: 'diagram',
  group: 'block',
  atom: true,

  addAttributes() {
    return { source: { default: '' } }
  },

  parseHTML() {
    return [
      {
        tag: 'figure[data-diagram-source]',
        getAttrs: (el: HTMLElement) => ({ source: el.dataset.diagramSource }),
      },
    ]
  },

  renderHTML({ node }) {
    return ['figure', { 'data-diagram-source': node.attrs.source }, ['pre', node.attrs.source]]
  },

  addNodeView() {
    return ({ node }) => {
      const dom = document.createElement('div')
      dom.className = 'diagram-node'
      dom.contentEditable = 'false'
      const figure = document.createElement('figure')
      figure.className = 'diagram'
      figure.dataset.diagram = ''
      const pre = document.createElement('pre')
      pre.className = 'diagram-source'
      pre.textContent = node.attrs.source
      figure.append(pre)
      dom.append(figure)
      renderDiagrams(dom).catch(() => {})
      return { dom }
    }
  },

  markdownTokenizer: {
    name: 'diagram',
    level: 'block',
    start: (src: string) => src.search(/^```mermaid/m),
    tokenize(src: string) {
      const match = /^```mermaid[ \t]*\n([\s\S]*?)\n```[ \t]*(?:\n|$)/.exec(src)
      if (!match) return undefined
      return { type: 'diagram', raw: match[0], source: match[1] }
    },
  },

  parseMarkdown(token: MarkdownToken, helpers) {
    return helpers.createNode('diagram', { source: token.source })
  },

  renderMarkdown(node) {
    return '```mermaid\n' + (node.attrs?.source ?? '') + '\n```'
  },
})
