<script setup lang="ts">
import {
  Check,
  GraduationCap,
  History,
  NotebookPen,
  ScrollText,
  Sparkles,
  Wand2,
} from 'lucide-vue-next'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate, useRoute, useRouter } from 'vue-router'
import { api } from '../api/client'
import { errorMessage } from '../api/errors'
import type { Chapter, Course, NoteSource } from '../api/types'
import AiProgress from '../components/AiProgress.vue'
import ChapterHeader from '../components/ChapterHeader.vue'
import CoursePanel from '../components/CoursePanel.vue'
import NotesHistory from '../components/NotesHistory.vue'
import NotesWorkspace from '../components/NotesWorkspace.vue'
import StudySection from '../components/StudySection.vue'
import { useAutosave } from '../composables/useAutosave'
import { countSpots } from '../lib/notesFormat'
import { subjectVars } from '../lib/subjects'
import { useSubjects } from '../stores/subjects'

type Tab = 'notes' | 'cours' | 'reviser'

const props = defineProps<{ id: string }>()
const route = useRoute()
const router = useRouter()
const { refresh: refreshSubjects } = useSubjects()
const chapterId = computed(() => Number(props.id))

const chapter = ref<Chapter>()
const notes = ref('')
const source = ref<NoteSource>('keyboard')
const course = ref<Course | null>(null)
const coursePanel = ref<InstanceType<typeof CoursePanel>>()
const pendingCount = ref(0)
const loadError = ref('')
const actionError = ref('')
const structuring = ref(false)

const TABS: { id: Tab; label: string; icon: unknown }[] = [
  { id: 'notes', label: 'Mes notes', icon: NotebookPen },
  { id: 'cours', label: 'Mon cours', icon: ScrollText },
  { id: 'reviser', label: 'Réviser', icon: GraduationCap },
]

const tab = computed<Tab>(() => {
  const value = route.query.onglet
  if (typeof value === 'string' && TABS.some((t) => t.id === value)) return value as Tab
  return course.value ? 'cours' : 'notes'
})

function selectTab(value: Tab): void {
  router.replace({ query: { ...route.query, onglet: value } })
}

// Titre proposé par la mise au propre, quand il diffère du nom donné au chapitre.
const dismissedTitle = ref('')
const proposedTitle = computed(() => {
  const title = course.value?.title?.trim() ?? ''
  const normalize = (value: string) =>
    value
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-z0-9]+/g, ' ')
      .trim()
  if (!title || title.includes('[illisible]') || title === dismissedTitle.value) return ''
  return normalize(title) === normalize(chapter.value?.title ?? '') ? '' : title
})

async function adoptTitle(): Promise<void> {
  try {
    chapter.value = await api.renameChapter(chapterId.value, proposedTitle.value)
    refreshSubjects().catch(() => {})
  } catch (e) {
    actionError.value = errorMessage(e)
  }
}

// Après l'import d'une photo, la sauvegarde suivante garde aussi une version des notes.
let photoCheckpoint = false

const autosave = useAutosave(async (keepalive) => {
  const id = chapterId.value
  const checkpoint = photoCheckpoint ? 'photo' : undefined
  photoCheckpoint = false
  try {
    await api.saveNotes(id, notes.value, source.value, { keepalive, checkpoint })
  } catch (error) {
    if (checkpoint) photoCheckpoint = true
    throw error
  }
  if (course.value && !keepalive) course.value = await api.course(id)
})

const historyOpen = ref(false)
const restoringNotes = ref(false)

async function restoreNotes(versionId: number): Promise<void> {
  if (!window.confirm('Remettre cette version de tes notes ? Tes notes actuelles seront gardées.'))
    return
  actionError.value = ''
  restoringNotes.value = true
  try {
    await autosave.flush()
    const restored = await api.restoreNoteVersion(chapterId.value, versionId)
    notes.value = restored.raw_text
    source.value = restored.source
    historyOpen.value = false
    if (course.value) course.value = await api.course(chapterId.value)
  } catch (e) {
    actionError.value = errorMessage(e)
  } finally {
    restoringNotes.value = false
  }
}

const saveLabel = computed(
  () =>
    ({
      saved: 'Sauvegardé',
      pending: 'Modifications en attente…',
      saving: 'Sauvegarde…',
      error: 'Échec de la sauvegarde',
    })[autosave.status.value],
)

async function load(): Promise<void> {
  loadError.value = ''
  actionError.value = ''
  historyOpen.value = false
  try {
    const id = chapterId.value
    const [loadedChapter, loadedNotes, loadedCourse] = await Promise.all([
      api.chapter(id),
      api.notes(id),
      api.course(id),
    ])
    chapter.value = loadedChapter
    notes.value = loadedNotes.raw_text
    source.value = loadedNotes.source
    course.value = loadedCourse
    pendingCount.value = loadedChapter.progress?.pending_suggestions ?? 0
  } catch (e) {
    loadError.value = errorMessage(e)
  }
}

/** Toute modification des notes (frappe, photo, vérification, schéma) est sauvegardée. */
function onNotesChanged(value: string): void {
  notes.value = value
  autosave.schedule()
}

function onTyping(): void {
  if (source.value === 'photo') source.value = 'mixed'
  autosave.schedule()
}

// Photo importée : la source des notes l'indique (clavier, photo, mélange).
function onCaptured(wasEmpty: boolean): void {
  source.value = wasEmpty || source.value === 'photo' ? 'photo' : 'mixed'
  photoCheckpoint = true
  autosave.schedule()
}

async function retrySave(): Promise<void> {
  actionError.value = ''
  try {
    await autosave.flush()
  } catch (e) {
    actionError.value = errorMessage(e)
  }
}

async function structure(): Promise<void> {
  const spots = countSpots(notes.value)
  if (
    spots &&
    !window.confirm(
      `Il reste ${spots} passage${spots > 1 ? 's' : ''} à vérifier dans tes notes ` +
        '(mots difficiles à lire sur la photo). Mettre le cours au propre quand même ?',
    )
  ) {
    return
  }
  if (
    course.value?.has_manual_changes &&
    !window.confirm(
      'Le cours a été modifié depuis la dernière mise au propre. ' +
        'Tes modifications resteront disponibles dans l’historique. Continuer ?',
    )
  ) {
    return
  }
  actionError.value = ''
  structuring.value = true
  try {
    await autosave.flush()
    course.value = await api.structure(chapterId.value)
    selectTab('cours')
    // L'IA relit tout de suite le nouveau cours ; les points à regarder s'affichent à côté.
    await nextTick()
    coursePanel.value?.review()
  } catch (e) {
    actionError.value = errorMessage(e)
    selectTab('notes')
  } finally {
    structuring.value = false
  }
}

// Après suppression, inutile de sauvegarder les notes en quittant la page.
let deleted = false

/** Le chapitre est à la corbeille : retour à sa matière. */
async function onDeleted(): Promise<void> {
  deleted = true
  refreshSubjects().catch(() => {})
  if (chapter.value)
    await router.push({ name: 'subject', params: { slug: chapter.value.subject.slug } })
}

async function leaveGuard(): Promise<boolean> {
  if (deleted) return true
  try {
    await autosave.flush()
    return true
  } catch {
    return window.confirm("Tes notes n'ont pas pu être sauvegardées. Quitter quand même ?")
  }
}

function onBeforeUnload(event: BeforeUnloadEvent): void {
  if (!autosave.hasUnsavedChanges()) return
  autosave.flush(true).catch(() => {})
  event.preventDefault()
}

onMounted(() => {
  window.addEventListener('beforeunload', onBeforeUnload)
})
onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', onBeforeUnload)
})
onBeforeRouteLeave(leaveGuard)
onBeforeRouteUpdate((to, from) => (to.params.id === from.params.id ? true : leaveGuard()))
watch(chapterId, load, { immediate: true })
</script>

<template>
  <p v-if="loadError" class="message error" role="alert">{{ loadError }}</p>

  <template v-if="chapter">
    <ChapterHeader
      :chapter="chapter"
      :has-course="!!course"
      @renamed="chapter = $event"
      @deleted="onDeleted"
      @error="actionError = $event"
    />

    <p v-if="actionError" class="message error" role="alert">{{ actionError }}</p>

    <div v-if="proposedTitle && tab === 'cours'" class="title-proposal" role="status">
      <Sparkles :size="18" aria-hidden="true" />
      <p>
        Titre proposé : <strong>« {{ proposedTitle }} »</strong>
      </p>
      <div class="toolbar">
        <button type="button" class="secondary" @click="adoptTitle">Utiliser</button>
        <button type="button" class="ghost" @click="dismissedTitle = proposedTitle">
          Garder le mien
        </button>
      </div>
    </div>

    <div
      class="tabs"
      role="tablist"
      aria-label="Étapes du chapitre"
      :style="subjectVars(chapter.subject.slug)"
    >
      <button
        v-for="(item, index) in TABS"
        :id="`tab-${item.id}`"
        :key="item.id"
        type="button"
        role="tab"
        class="tab"
        :aria-selected="tab === item.id"
        :aria-controls="`panel-${item.id}`"
        @click="selectTab(item.id)"
      >
        <span class="step-number" aria-hidden="true">{{ index + 1 }}</span>
        {{ item.label }}
        <span v-if="item.id === 'cours' && pendingCount" class="badge-count">
          {{ pendingCount }}<span class="visually-hidden"> en attente</span>
        </span>
        <span
          v-if="item.id === 'notes' && course?.notes_changed"
          class="warning-dot"
          title="Notes modifiées depuis la mise au propre"
        />
      </button>
    </div>

    <section
      v-show="tab === 'notes'"
      id="panel-notes"
      class="card"
      role="tabpanel"
      aria-labelledby="tab-notes"
    >
      <div class="section-header">
        <h2>Mes notes</h2>
        <button
          type="button"
          class="ghost history-toggle"
          :aria-expanded="historyOpen"
          @click="historyOpen = !historyOpen"
        >
          <History :size="18" aria-hidden="true" /> Historique
        </button>
      </div>

      <NotesHistory
        v-if="historyOpen"
        :chapter-id="chapterId"
        :restoring="restoringNotes"
        @restore="restoreNotes"
        @close="historyOpen = false"
      />

      <NotesWorkspace
        :model-value="notes"
        :chapter-id="chapterId"
        @update:model-value="onNotesChanged"
        @typed="onTyping"
        @captured="onCaptured"
      />

      <div class="action-bar">
        <button
          type="button"
          class="primary big"
          :disabled="structuring || !notes.trim()"
          @click="structure"
        >
          <Wand2 :size="22" aria-hidden="true" />
          {{ course ? 'Remettre le cours au propre' : 'Mettre le cours au propre' }}
        </button>
        <AiProgress operation="structure" :running="structuring" title="Mise au propre du cours" />
        <p class="save-status" :class="autosave.status.value" aria-live="polite">
          <Check v-if="autosave.status.value === 'saved'" :size="16" aria-hidden="true" />
          {{ saveLabel }}
          <button
            v-if="autosave.status.value === 'error'"
            type="button"
            class="link"
            @click="retrySave"
          >
            Réessayer
          </button>
        </p>
      </div>
    </section>

    <div
      v-show="tab === 'cours'"
      id="panel-cours"
      role="tabpanel"
      aria-labelledby="tab-cours"
      :style="subjectVars(chapter.subject.slug)"
    >
      <CoursePanel
        v-if="course"
        ref="coursePanel"
        v-model:course="course"
        :chapter-id="chapterId"
        :notes="notes"
        @restructure="structure"
        @pending="pendingCount = $event"
      />
      <div v-else class="empty-state">
        <ScrollText :size="34" aria-hidden="true" />
        <strong>Ton cours propre apparaîtra ici</strong>
        <span>Écris tes notes, puis clique sur « Mettre le cours au propre ».</span>
        <button type="button" class="primary" @click="selectTab('notes')">
          <NotebookPen :size="20" aria-hidden="true" /> Aller à mes notes
        </button>
      </div>
    </div>

    <div
      v-show="tab === 'reviser'"
      id="panel-reviser"
      role="tabpanel"
      aria-labelledby="tab-reviser"
      :style="subjectVars(chapter.subject.slug)"
    >
      <StudySection v-if="course" :chapter-id="chapterId" :course-version="course.version" />
      <div v-else class="empty-state">
        <GraduationCap :size="34" aria-hidden="true" />
        <strong>Révisions bientôt disponibles</strong>
        <span>Fiche de révision et quiz se créent à partir de ton cours propre.</span>
      </div>
    </div>
  </template>
</template>

<style scoped>
.grow {
  flex: 1;
  min-width: 0;
}
</style>
