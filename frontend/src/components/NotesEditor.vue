<script setup lang="ts">
import type { Editor } from '@tiptap/core'
import { EditorContent, useEditor } from '@tiptap/vue-3'
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { notesEditorExtensions, type SpotClick } from '../lib/notesEditor'
import { docToNotes, notesToDoc, type UncertainSpot } from '../lib/notesFormat'

const props = defineProps<{ modelValue: string }>()
const emit = defineEmits<{ 'update:modelValue': [value: string]; typed: [] }>()

// Bulle de vérification d'un passage incertain.
const open = ref<{ pos: number; spot: UncertainSpot; top: number; left: number } | null>(null)
const custom = ref('')
const wrapper = ref<HTMLElement>()
const customInput = ref<HTMLInputElement>()
let lastEmitted = props.modelValue
let programmatic = false
// Tant que l'élève n'a pas cliqué dans ses notes, les photos s'ajoutent à la fin.
let focusedOnce = false

const editor = useEditor({
  extensions: notesEditorExtensions(openSpot),
  content: notesToDoc(props.modelValue),
  editorProps: {
    attributes: { class: 'notes-editor-content', 'aria-label': 'Mes notes', spellcheck: 'true' },
  },
  onCreate: ({ editor: current }) => refreshSpots(current),
  onFocus: () => {
    focusedOnce = true
  },
  onUpdate: ({ editor: current }) => {
    refreshSpots(current)
    lastEmitted = docToNotes(current.getJSON())
    emit('update:modelValue', lastEmitted)
    if (!programmatic) emit('typed')
  },
})

// Notes rechargées depuis le serveur (changement de chapitre…).
watch(
  () => props.modelValue,
  (value) => {
    if (value !== lastEmitted && editor.value) {
      lastEmitted = value
      editor.value.commands.setContent(notesToDoc(value), { emitUpdate: false })
      refreshSpots()
    }
  },
)

onBeforeUnmount(() => editor.value?.destroy())

// L'événement de création de TipTap arrive en différé : on compte dès que l'éditeur existe.
watch(editor, (current) => refreshSpots(current))

/** Passages restant à vérifier (positions dans le document), tenus à jour. */
const spots = ref<{ pos: number; spot: UncertainSpot }[]>([])

function refreshSpots(current: Editor | undefined = editor.value): void {
  const found: { pos: number; spot: UncertainSpot }[] = []
  current?.state.doc.descendants((node, pos) => {
    if (node.type.name === 'uncertain') found.push({ pos, spot: node.attrs as UncertainSpot })
  })
  spots.value = found
}

function openSpot({ pos, spot, element }: SpotClick): void {
  const box = wrapper.value?.getBoundingClientRect()
  const rect = element.getBoundingClientRect()
  // La fenêtre reste dans l'éditeur, même sur un téléphone (22rem au plus, voir styles.css).
  const width = Math.min(22 * 16, box?.width ?? Infinity)
  const maxLeft = Math.max(0, (box?.width ?? width) - width)
  open.value = {
    pos,
    spot,
    top: rect.bottom - (box?.top ?? 0) + 6,
    left: Math.min(maxLeft, Math.max(0, rect.left - (box?.left ?? 0))),
  }
  custom.value = ''
  nextTick(() => customInput.value?.focus())
}

function withProgram(action: () => void): void {
  programmatic = true
  action()
  programmatic = false
}

/** Remplace le passage par le texte choisi (il n'est plus à vérifier). */
function resolve(text: string): void {
  if (!open.value || !editor.value || !text.trim()) return
  const { pos } = open.value
  withProgram(() =>
    editor
      .value!.chain()
      .focus()
      .insertContentAt({ from: pos, to: pos + 1 }, text.trim())
      .run(),
  )
  open.value = null
}

function keepIllegible(): void {
  if (!open.value || !editor.value) return
  const { pos } = open.value
  withProgram(() =>
    editor
      .value!.chain()
      .focus()
      .command(({ tr }) => {
        tr.setNodeMarkup(pos, undefined, { guess: '', options: [] })
        return true
      })
      .run(),
  )
  open.value = null
}

/** Ouvre le passage suivant à vérifier. */
function nextSpot(): void {
  const list = spots.value
  if (!list.length || !editor.value) return
  const after = editor.value.state.selection.to
  const target = list.find((s) => s.pos >= after) ?? list[0]!
  const element = editor.value.view.nodeDOM(target.pos) as HTMLElement | null
  if (!element) return
  element.scrollIntoView?.({ block: 'center', behavior: 'smooth' })
  editor.value.commands.setNodeSelection(target.pos)
  openSpot({ pos: target.pos, spot: target.spot, element })
}

/** Place le curseur à la fin tant que l'élève n'a pas choisi d'endroit dans ses notes. */
function insertionPoint() {
  const current = editor.value!
  return focusedOnce ? current.chain().focus() : current.chain().focus('end')
}

/** Insère un bloc de notes (texte lu sur une photo, avec ses passages incertains). */
function insertBlock(notes: string): void {
  const current = editor.value
  if (!current) return
  const empty = !current.getText().trim()
  const blocks = notesToDoc(notes).content ?? []
  withProgram(() => {
    if (empty) current.chain().focus().setContent({ type: 'doc', content: blocks }).run()
    else insertionPoint().selectTextblockEnd().insertContent(blocks).run()
  })
  refreshSpots(current)
  lastEmitted = docToNotes(current.getJSON())
  emit('update:modelValue', lastEmitted)
}

function insertImage(src: string, alt: string): void {
  if (!editor.value) return
  withProgram(() =>
    insertionPoint()
      .selectTextblockEnd()
      .insertContent({ type: 'image', attrs: { src, alt } })
      .run(),
  )
}

defineExpose({ insertBlock, insertImage, nextSpot, spots })
</script>

<template>
  <div ref="wrapper" class="notes-editor" @keydown.esc="open = null">
    <EditorContent :editor="editor" />

    <div
      v-if="open"
      class="spot-popover"
      role="dialog"
      aria-label="Vérifier un passage"
      :style="{ top: `${open.top}px`, left: `${open.left}px` }"
    >
      <p class="spot-popover-title">
        {{
          open.spot.guess ? 'Mot difficile à lire. C’est bien :' : 'Passage illisible. Peut-être :'
        }}
      </p>
      <div class="spot-choices">
        <button
          v-if="open.spot.guess"
          type="button"
          class="primary"
          @click="resolve(open.spot.guess)"
        >
          {{ open.spot.guess }}
        </button>
        <button
          v-for="option in open.spot.options"
          :key="option"
          type="button"
          class="secondary"
          @click="resolve(option)"
        >
          {{ option }}
        </button>
      </div>
      <form class="spot-custom" @submit.prevent="resolve(custom)">
        <label for="spot-custom" class="visually-hidden">Ce que je lis dans mon cahier</label>
        <input
          id="spot-custom"
          ref="customInput"
          v-model="custom"
          type="text"
          placeholder="Ce que je lis dans mon cahier…"
        />
        <button type="submit" :disabled="!custom.trim()">OK</button>
      </form>
      <div class="spot-actions">
        <button v-if="open.spot.guess" type="button" class="link" @click="keepIllegible">
          Je ne sais pas (illisible)
        </button>
        <button type="button" class="link" @click="open = null">Fermer</button>
      </div>
    </div>
  </div>
</template>
