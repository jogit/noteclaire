import { enableAutoUnmount } from '@vue/test-utils'
import { afterEach } from 'vitest'
// jsdom ne calcule pas la mise en page : on fournit ce dont l'éditeur (ProseMirror) a besoin.
const emptyRect = { x: 0, y: 0, top: 0, left: 0, right: 0, bottom: 0, width: 0, height: 0 }
const rects = () => Object.assign([], { item: () => null }) as unknown as DOMRectList

Range.prototype.getClientRects = rects
Range.prototype.getBoundingClientRect = () => ({ ...emptyRect, toJSON: () => emptyRect }) as DOMRect
Element.prototype.getClientRects = rects
Element.prototype.scrollIntoView = () => {}

// Chaque composant est démonté après son test : ses minuteries et écouteurs (sauvegarde
// automatique, progression IA, sélection…) ne débordent pas sur les tests suivants.
enableAutoUnmount(afterEach)
