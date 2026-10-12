/** Extensions de l'éditeur de notes : texte simple, images et passages incertains. */
import { Node, type AnyExtension } from '@tiptap/core'
import Document from '@tiptap/extension-document'
import Image from '@tiptap/extension-image'
import Paragraph from '@tiptap/extension-paragraph'
import Text from '@tiptap/extension-text'
import { Placeholder, UndoRedo } from '@tiptap/extensions'
import { spotMarker, type UncertainSpot } from './notesFormat'

export interface SpotClick {
  pos: number
  spot: UncertainSpot
  element: HTMLElement
}

/** Passage incertain lu sur une photo : étiquette cliquable. */
const Uncertain = Node.create<{ onOpen: (click: SpotClick) => void }>({
  name: 'uncertain',
  group: 'inline',
  inline: true,
  atom: true,
  selectable: true,

  addOptions() {
    return { onOpen: () => {} }
  },

  addAttributes() {
    return { guess: { default: '' }, options: { default: [] } }
  },

  renderHTML({ node }) {
    return ['span', { 'data-uncertain': '' }, spotMarker(node.attrs as UncertainSpot)]
  },

  addNodeView() {
    return ({ node, getPos }) => {
      const spot = node.attrs as UncertainSpot
      const dom = document.createElement('button')
      dom.type = 'button'
      dom.contentEditable = 'false'
      dom.className = spot.guess ? 'spot spot-doubt' : 'spot spot-illegible'
      dom.textContent = spot.guess || 'illisible'
      dom.setAttribute(
        'aria-label',
        spot.guess ? `Mot incertain : ${spot.guess}. Vérifier` : 'Passage illisible. Compléter',
      )
      dom.addEventListener('click', (event) => {
        event.preventDefault()
        const pos = typeof getPos === 'function' ? getPos() : undefined
        if (typeof pos === 'number') this.options.onOpen({ pos, spot, element: dom })
      })
      return { dom }
    }
  },
})

export function notesEditorExtensions(onOpen: (click: SpotClick) => void): AnyExtension[] {
  return [
    Document,
    Paragraph,
    Text,
    UndoRedo,
    Image.configure({ inline: false }),
    Uncertain.configure({ onOpen }),
    Placeholder.configure({
      placeholder: 'Tape tes notes ici, ou utilise « Photos des notes ».',
    }),
  ]
}
