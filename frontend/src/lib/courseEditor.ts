import type { AnyExtension } from '@tiptap/core'
import Highlight from '@tiptap/extension-highlight'
import Image from '@tiptap/extension-image'
import { OrderedList } from '@tiptap/extension-list'
import { TableKit } from '@tiptap/extension-table'
import { Markdown } from '@tiptap/markdown'
import StarterKit from '@tiptap/starter-kit'
import { Callout, Diagram, MathBlock, MathInline } from './editorExtensions'

const baseTokenizer = OrderedList.config.markdownTokenizer!

/**
 * Listes numérotées : seulement « 1. » ou « 1) », comme le Markdown standard.
 * TipTap accepte aussi « a. » ou « iv. », ce qui transformait « Ex. : … » en liste.
 */
const NumericOrderedList = OrderedList.extend({
  markdownTokenizer: {
    ...baseTokenizer,
    tokenize: (src, tokens, lexer) =>
      /^\s*\d+[.)]\s/.test(src) ? baseTokenizer.tokenize(src, tokens, lexer) : undefined,
  },
})

/** Extensions de l'éditeur visuel du cours (partagées avec les tests). */
export function courseEditorExtensions(): AnyExtension[] {
  return [
    StarterKit.configure({ link: false, underline: false, orderedList: false }),
    NumericOrderedList,
    Highlight,
    Image,
    TableKit,
    Callout,
    MathInline,
    MathBlock,
    Diagram,
    Markdown,
  ]
}

/**
 * Markdown du cours tel que l'éditeur l'écrit, sans les crochets échappés (« \[illisible\] »,
 * « \[schéma : …\] ») que la mise au propre et l'affichage utilisent tels quels.
 * Les formules ($…$) ne sont pas touchées.
 */
export function courseMarkdown(editor: { getMarkdown: () => string }): string {
  return editor
    .getMarkdown()
    .split(/(\$\$[\s\S]*?\$\$|\$[^$\n]*\$)/)
    .map((part, index) => (index % 2 ? part : part.replace(/\\([[\]])/g, '$1')))
    .join('')
    .trim()
}
