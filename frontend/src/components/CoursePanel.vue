<script setup lang="ts">
import { ArrowLeft, GitCompareArrows, History, Pencil, X } from 'lucide-vue-next'
import {
  computed,
  defineAsyncComponent,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from 'vue'
import { api } from '../api/client'
import { errorMessage } from '../api/errors'
import type { Course, Suggestion } from '../api/types'
import { renderInlineMarkdown, replaceSchema } from '../lib/markdown'
import { selectionText } from '../lib/selectionText'
import { ANCHOR_CLASS, anchorSuggestions } from '../lib/suggestionAnchors'
import { compareNotesAndCourse, REMOVED_TEXT_WARNING_RATIO } from '../lib/textDiff'
import CourseDiff from './CourseDiff.vue'
import CourseEditor from './CourseEditor.vue'
import ExplainPanel from './ExplainPanel.vue'
import MarkdownContent from './MarkdownContent.vue'
import ReviewPanel from './ReviewPanel.vue'
import VersionHistory from './VersionHistory.vue'

type Mode = 'view' | 'diff' | 'edit' | 'history'

const props = defineProps<{ chapterId: number; notes: string; course: Course }>()
const emit = defineEmits<{
  'update:course': [course: Course]
  restructure: []
  pending: [count: number]
}>()

// L'éditeur visuel (TipTap) n'est chargé qu'au premier clic sur « Modifier ».
const RichCourseEditor = defineAsyncComponent(() => import('./RichCourseEditor.vue'))

// La lecture du cours est l'affichage normal ; les autres vues s'ouvrent depuis ces boutons.
const ACTIONS: { mode: Mode; label: string; icon: unknown }[] = [
  { mode: 'edit', label: 'Modifier', icon: Pencil },
  { mode: 'diff', label: "Ce que l'IA a changé", icon: GitCompareArrows },
  { mode: 'history', label: 'Versions', icon: History },
]
const TITLES: Record<Mode, string> = {
  view: '',
  edit: 'Modifier le cours',
  diff: "Ce que l'IA a changé par rapport à tes notes",
  history: 'Versions du cours',
}

const mode = ref<Mode>('view')

function toggleMode(value: Mode): void {
  mode.value = mode.value === value ? 'view' : value
}

// Au changement d'affichage, le focus va sur ce qui vient d'apparaître (pratique au clavier) ;
// le bouton cliqué ne garde pas son contour de focus.
const modeTitle = ref<HTMLElement>()
const courseView = ref<HTMLElement>()
watch(mode, async (value) => {
  await nextTick()
  const target = value === 'view' ? courseView.value : modeTitle.value
  target?.focus({ preventScroll: true })
})

// Relecture : seul le passage du point affiché est surligné (les autres restent invisibles).
const review = ref<InstanceType<typeof ReviewPanel>>()
const suggestions = ref<Suggestion[]>([])
const anchored = ref(new Set<number>())
const focusedId = ref<number | null>(null)

function onSuggestions(list: Suggestion[]): void {
  suggestions.value = list
  emit('pending', list.length)
}

async function refreshAnchors(): Promise<void> {
  await nextTick()
  if (mode.value !== 'view' || !courseContent.value) {
    anchored.value = new Set()
    return
  }
  anchored.value = anchorSuggestions(courseContent.value, suggestions.value)
  showFocused(false)
}

watch([suggestions, () => props.course.content_markdown, mode], refreshAnchors)

function showFocused(scroll: boolean): void {
  let target: HTMLElement | undefined
  courseContent.value?.querySelectorAll<HTMLElement>(`mark.${ANCHOR_CLASS}`).forEach((mark) => {
    const active = mark.dataset.suggestionId === String(focusedId.value)
    mark.classList.toggle('active', active)
    if (active) target ??= mark
  })
  // En haut de l'écran : le panneau de relecture occupe le bas.
  if (scroll) target?.scrollIntoView?.({ behavior: 'smooth', block: 'start' })
}

async function onFocus(id: number | null): Promise<void> {
  focusedId.value = id
  await nextTick() // l'espace réservé sous le cours doit exister avant de faire défiler
  showFocused(true)
}

// Relecture automatique après une mise au propre : sans confirmation (nouveau cours).
defineExpose({ review: () => review.value?.analyze(false) })
// Éditeur choisi (visuel ou Markdown), mémorisé dans ce navigateur.
const EDITOR_KEY = 'noteclaire.courseEditor'
function storedEditor(): boolean {
  try {
    return localStorage.getItem(EDITOR_KEY) === 'markdown'
  } catch {
    return false
  }
}
const advanced = ref(storedEditor())
// Modifications en cours, gardées quand on passe d'un éditeur à l'autre.
const editDraft = ref<string>()

function switchEditor(markdown: boolean, draft: string): void {
  editDraft.value = draft === props.course.content_markdown ? undefined : draft
  advanced.value = markdown
  try {
    localStorage.setItem(EDITOR_KEY, markdown ? 'markdown' : 'visual')
  } catch {
    // Préférence non mémorisée : sans conséquence.
  }
}

watch(mode, () => (editDraft.value = undefined))
const saving = ref(false)
const error = ref('')

// « Je n'ai pas compris » (SPEC §19) : passage sélectionné dans le cours affiché.
const courseContent = ref<HTMLElement>()
const selectedPassage = ref('')
const explaining = ref('')

// Clic dans le bandeau : la sélection disparaît, mais le bandeau doit rester (son bouton).
let pointerInBar = false

function onPointerDown(event: PointerEvent): void {
  pointerInBar = !!(event.target as HTMLElement | null)?.closest?.('.selection-bar')
}

function onSelectionChange(): void {
  const selection = document.getSelection()
  if (!selection?.toString().trim()) {
    // Clic ailleurs : la sélection est annulée, le bandeau s'en va avec elle.
    if (!pointerInBar) selectedPassage.value = ''
    return
  }
  if (!selection.anchorNode || !courseContent.value?.contains(selection.anchorNode)) return
  const text = selectionText(selection.getRangeAt(0))
  if (text) selectedPassage.value = text.slice(0, 2000)
}

function onKeyDown(event: KeyboardEvent): void {
  if (event.key === 'Escape' && selectedPassage.value) closeSelection()
}

function closeSelection(): void {
  selectedPassage.value = ''
  document.getSelection()?.removeAllRanges()
}

onMounted(() => {
  document.addEventListener('selectionchange', onSelectionChange)
  document.addEventListener('pointerdown', onPointerDown, true)
  document.addEventListener('keydown', onKeyDown)
})
onBeforeUnmount(() => {
  document.removeEventListener('selectionchange', onSelectionChange)
  document.removeEventListener('pointerdown', onPointerDown, true)
  document.removeEventListener('keydown', onKeyDown)
})

function openExplain(): void {
  explaining.value = selectedPassage.value
  selectedPassage.value = ''
  document.getSelection()?.removeAllRanges()
}

// Protection des notes : avertit si la mise au propre a fait disparaître une partie du texte.
const removedPercent = computed(() => {
  if (props.course.notes_changed) return 0
  const ratio = compareNotesAndCourse(props.notes, props.course.content_markdown).netRemovedRatio
  return ratio > REMOVED_TEXT_WARNING_RATIO ? Math.round(ratio * 100) : 0
})

// Photo d'un schéma relevé comme « [schéma : …] » lors de la lecture d'une photo.
const schemaInput = ref<HTMLInputElement>()
const schemaIndex = ref(0)
const uploading = ref(false)

function pickSchemaImage(index: number): void {
  schemaIndex.value = index
  schemaInput.value?.click()
}

async function onSchemaImage(event: Event): Promise<void> {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (schemaInput.value) schemaInput.value.value = ''
  if (!file) return
  uploading.value = true
  error.value = ''
  try {
    const { url } = await api.uploadImage(props.chapterId, file)
    await save(replaceSchema(props.course.content_markdown, schemaIndex.value, url))
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    uploading.value = false
  }
}

async function save(content: string): Promise<void> {
  saving.value = true
  error.value = ''
  try {
    emit('update:course', await api.updateCourse(props.chapterId, content))
    mode.value = 'view'
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <section class="card course-card" aria-labelledby="course-title">
    <div class="section-header">
      <h2 id="course-title">
        Mon cours <span class="hint course-version">version {{ course.version }}</span>
      </h2>
      <div class="toolbar course-actions" role="group" aria-label="Autres affichages du cours">
        <button
          v-for="action in ACTIONS"
          :key="action.mode"
          type="button"
          class="ghost"
          :aria-pressed="mode === action.mode"
          @click="toggleMode(action.mode)"
        >
          <component :is="action.icon" :size="18" aria-hidden="true" />
          {{ action.label }}
        </button>
      </div>
    </div>

    <div v-if="course.notes_changed" class="message warning" role="status">
      <p><strong>⚠ Tes notes ont changé depuis la dernière mise au propre.</strong></p>
      <button type="button" class="secondary" @click="emit('restructure')">
        Remettre le cours au propre
      </button>
    </div>
    <div v-if="removedPercent" class="message warning" role="status">
      <p>
        <strong
          >⚠ Environ {{ removedPercent }} % de tes notes ne se retrouvent pas dans le cours.</strong
        >
      </p>
      <button type="button" class="secondary" @click="mode = 'diff'">
        Voir ce que l'IA a changé
      </button>
    </div>
    <p v-if="error" class="message error" role="alert">{{ error }}</p>

    <div v-if="mode !== 'view'" class="course-mode">
      <div class="mode-header">
        <button type="button" class="ghost" @click="mode = 'view'">
          <ArrowLeft :size="18" aria-hidden="true" /> Revenir au cours
        </button>
        <h3 ref="modeTitle" tabindex="-1">{{ TITLES[mode] }}</h3>
      </div>

      <template v-if="mode === 'diff'">
        <p v-if="course.notes_changed">
          La comparaison n'est possible qu'avec les notes utilisées pour ce cours. Remets le cours
          au propre pour comparer.
        </p>
        <CourseDiff v-else :notes="notes" :course="course.content_markdown" />
      </template>
      <template v-else-if="mode === 'edit'">
        <CourseEditor
          v-if="advanced"
          :content="course.content_markdown"
          :initial="editDraft"
          :saving="saving"
          @save="save"
          @cancel="mode = 'view'"
          @visual="switchEditor(false, $event)"
        />
        <RichCourseEditor
          v-else
          :key="course.version"
          :chapter-id="chapterId"
          :content="course.content_markdown"
          :draft="editDraft"
          :saving="saving"
          @save="save"
          @cancel="mode = 'view'"
          @advanced="switchEditor(true, $event)"
        />
      </template>
      <VersionHistory
        v-else
        :key="course.version"
        :chapter-id="chapterId"
        :current-version="course.version"
        :restoring="saving"
        @restore="save"
      />
    </div>

    <!-- Barre de relecture au-dessus, cours en dessous ; pendant la relecture, le panneau
         du point affiché se met à droite du cours (grand écran) ou en bas (petit écran). -->
    <div
      v-show="mode === 'view'"
      ref="courseView"
      class="course-view"
      :class="{ reviewing: focusedId !== null }"
      tabindex="-1"
    >
      <ReviewPanel
        ref="review"
        :chapter-id="chapterId"
        :course-version="course.version"
        :anchored="anchored"
        @update:course="emit('update:course', $event)"
        @suggestions="onSuggestions"
        @focus="onFocus"
      />
      <div class="course-main">
        <p v-if="!selectedPassage && !explaining" class="hint">
          Un passage pas clair ? Sélectionne-le dans le cours.
        </p>
        <div v-if="selectedPassage" class="selection-bar" role="status">
          <!-- eslint-disable-next-line vue/no-v-html -- markdown-it (html: false) -->
          <span class="selection-text" v-html="renderInlineMarkdown(`« ${selectedPassage} »`)" />
          <button type="button" class="primary" @click="openExplain">Je n'ai pas compris</button>
          <button type="button" class="icon ghost" aria-label="Fermer" @click="closeSelection">
            <X :size="20" aria-hidden="true" />
          </button>
        </div>
        <div ref="courseContent">
          <MarkdownContent
            :source="course.content_markdown"
            can-add-images
            @add-schema-image="pickSchemaImage"
          />
        </div>
        <input
          ref="schemaInput"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          class="visually-hidden"
          tabindex="-1"
          aria-hidden="true"
          @change="onSchemaImage"
        />
        <p v-if="uploading" class="hint" aria-live="polite">Ajout de l'image…</p>
        <ExplainPanel
          v-if="explaining"
          :key="explaining"
          :chapter-id="chapterId"
          :passage="explaining"
          @close="explaining = ''"
        />
      </div>
    </div>
  </section>
</template>
