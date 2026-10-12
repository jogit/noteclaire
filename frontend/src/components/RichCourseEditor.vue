<script setup lang="ts">
import { EditorContent, useEditor } from '@tiptap/vue-3'
import {
  Bold,
  Heading2,
  Heading3,
  Highlighter,
  ImagePlus,
  List,
  ListOrdered,
  Redo2,
  Sigma,
  Table,
  Undo2,
} from 'lucide-vue-next'
import { onBeforeUnmount, ref } from 'vue'
import { api } from '../api/client'
import { errorMessage } from '../api/errors'
import { courseEditorExtensions, courseMarkdown } from '../lib/courseEditor'
import { CALLOUTS, type CalloutType } from '../lib/markdown'

// `draft` : texte en cours de modification venu de l'éditeur Markdown (sinon le cours enregistré).
const props = defineProps<{ chapterId: number; content: string; saving: boolean; draft?: string }>()
const emit = defineEmits<{ save: [content: string]; cancel: []; advanced: [draft: string] }>()

const dirty = ref(props.draft !== undefined && props.draft !== props.content)
const error = ref('')
const imageInput = ref<HTMLInputElement>()
const uploading = ref(false)

const editor = useEditor({
  extensions: courseEditorExtensions(),
  content: props.draft ?? props.content,
  contentType: 'markdown',
  editorProps: { attributes: { class: 'markdown rich-editor-content', 'aria-label': 'Cours' } },
  onUpdate: () => {
    dirty.value = true
  },
})

onBeforeUnmount(() => editor.value?.destroy())

const chain = () => editor.value!.chain().focus()

function toggleCallout(type: CalloutType): void {
  if (!editor.value) return
  if (editor.value.isActive('callout', { type })) chain().lift('callout').run()
  else if (editor.value.isActive('callout')) chain().updateAttributes('callout', { type }).run()
  else chain().wrapIn('callout', { type, title: '' }).run()
}

function insertFormula(): void {
  const latex = window.prompt(
    'Formule (notation LaTeX) — exemples : x^2, \\frac{1}{2}, \\sqrt{x}, \\mathrm{H_2O}',
  )
  if (latex) chain().insertContent({ type: 'mathInline', attrs: { latex } }).run()
}

async function onImage(event: Event): Promise<void> {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (imageInput.value) imageInput.value.value = ''
  if (!file) return
  uploading.value = true
  error.value = ''
  try {
    const { url } = await api.uploadImage(props.chapterId, file)
    chain()
      .setImage({ src: url, alt: file.name.replace(/\.[^.]+$/, '') })
      .run()
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    uploading.value = false
  }
}

function save(): void {
  if (editor.value) emit('save', courseMarkdown(editor.value))
}

/** Passe à l'éditeur Markdown en gardant les modifications en cours. */
function toMarkdown(): void {
  if (!editor.value) return
  emit('advanced', dirty.value ? courseMarkdown(editor.value) : props.content)
}

function cancel(): void {
  if (!dirty.value || window.confirm('Abandonner tes modifications ?')) emit('cancel')
}
</script>

<template>
  <div class="rich-editor">
    <div v-if="editor" class="editor-toolbar" role="toolbar" aria-label="Mise en forme">
      <div class="toolbar-group">
        <button
          type="button"
          :aria-pressed="editor.isActive('heading', { level: 2 })"
          title="Titre"
          @click="chain().toggleHeading({ level: 2 }).run()"
        >
          <Heading2 :size="20" aria-hidden="true" /><span>Titre</span>
        </button>
        <button
          type="button"
          :aria-pressed="editor.isActive('heading', { level: 3 })"
          title="Sous-titre"
          @click="chain().toggleHeading({ level: 3 }).run()"
        >
          <Heading3 :size="20" aria-hidden="true" /><span>Sous-titre</span>
        </button>
      </div>
      <div class="toolbar-group">
        <button
          type="button"
          :aria-pressed="editor.isActive('bold')"
          title="Gras"
          @click="chain().toggleBold().run()"
        >
          <Bold :size="20" aria-hidden="true" /><span>Gras</span>
        </button>
        <button
          type="button"
          class="highlight-button"
          :aria-pressed="editor.isActive('highlight')"
          title="Surligner"
          @click="chain().toggleHighlight().run()"
        >
          <Highlighter :size="20" aria-hidden="true" /><span>Surligner</span>
        </button>
      </div>
      <div class="toolbar-group">
        <button
          type="button"
          :aria-pressed="editor.isActive('bulletList')"
          title="Liste à puces"
          @click="chain().toggleBulletList().run()"
        >
          <List :size="20" aria-hidden="true" /><span>Liste</span>
        </button>
        <button
          type="button"
          :aria-pressed="editor.isActive('orderedList')"
          title="Liste numérotée"
          @click="chain().toggleOrderedList().run()"
        >
          <ListOrdered :size="20" aria-hidden="true" /><span>Étapes</span>
        </button>
      </div>
      <div class="toolbar-group">
        <button type="button" title="Formule" @click="insertFormula">
          <Sigma :size="20" aria-hidden="true" /><span>Formule</span>
        </button>
        <button
          type="button"
          title="Image ou schéma"
          :disabled="uploading"
          @click="imageInput?.click()"
        >
          <ImagePlus :size="20" aria-hidden="true" /><span>Image</span>
        </button>
        <button
          type="button"
          title="Tableau"
          @click="chain().insertTable({ rows: 3, cols: 2, withHeaderRow: true }).run()"
        >
          <Table :size="20" aria-hidden="true" /><span>Tableau</span>
        </button>
      </div>
      <div class="toolbar-group">
        <button
          type="button"
          class="icon"
          aria-label="Annuler la dernière action"
          :disabled="!editor.can().undo()"
          @click="chain().undo().run()"
        >
          <Undo2 :size="20" aria-hidden="true" />
        </button>
        <button
          type="button"
          class="icon"
          aria-label="Rétablir"
          :disabled="!editor.can().redo()"
          @click="chain().redo().run()"
        >
          <Redo2 :size="20" aria-hidden="true" />
        </button>
      </div>
      <div class="callout-picker" role="group" aria-label="Encadrés">
        <span class="hint">Encadré :</span>
        <button
          v-for="(label, type) in CALLOUTS"
          :key="type"
          type="button"
          class="callout-chip"
          :class="`callout-${type}`"
          :aria-pressed="editor.isActive('callout', { type })"
          @click="toggleCallout(type)"
        >
          {{ label }}
        </button>
      </div>
    </div>

    <input
      ref="imageInput"
      type="file"
      accept="image/jpeg,image/png,image/webp"
      class="visually-hidden"
      tabindex="-1"
      aria-hidden="true"
      @change="onImage"
    />
    <p v-if="uploading" class="hint" aria-live="polite">Ajout de l'image…</p>
    <p v-if="error" class="message error" role="alert">{{ error }}</p>

    <EditorContent :editor="editor" class="rich-editor-frame" />

    <div class="actions">
      <button type="button" class="primary" :disabled="saving || !dirty" @click="save">
        Enregistrer
      </button>
      <button type="button" class="ghost" :disabled="saving" @click="cancel">Annuler</button>
      <button type="button" class="link advanced-link" @click="toMarkdown">
        Mode avancé (Markdown)
      </button>
    </div>
  </div>
</template>
