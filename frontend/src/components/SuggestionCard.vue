<script setup lang="ts">
import {
  BookMarked,
  CircleHelp,
  Crosshair,
  Lightbulb,
  MessageSquareText,
  PenLine,
  TriangleAlert,
} from 'lucide-vue-next'
import { computed, ref, type Component } from 'vue'
import { api } from '../api/client'
import { ApiError, errorMessage } from '../api/errors'
import type { Course, Occurrence, Suggestion, SuggestionType } from '../api/types'
import { markdownExcerpt, renderInlineMarkdown } from '../lib/markdown'
import MarkdownContent from './MarkdownContent.vue'

const props = defineProps<{ suggestion: Suggestion; anchored?: boolean }>()
const emit = defineEmits<{ decided: [id: number, course: Course | null]; show: [] }>()

const LABELS: Record<SuggestionType, { icon: Component; title: string }> = {
  correction: { icon: PenLine, title: 'Correction proposée' },
  clarification: { icon: MessageSquareText, title: 'Précision proposée' },
  missing_information: { icon: CircleHelp, title: 'Information à compléter' },
  addition: { icon: Lightbulb, title: 'Complément proposé' },
  warning: { icon: TriangleAlert, title: 'À vérifier' },
}

const busy = ref(false)
const error = ref('')
const occurrences = ref<Occurrence[]>([])
const outdated = ref(false)

const label = computed(() => LABELS[props.suggestion.type])
const isAddition = computed(() => props.suggestion.type === 'addition')
// Passage après lequel le complément sera ajouté : rendu comme le cours (formules comprises).
const afterExcerpt = computed(() =>
  renderInlineMarkdown(markdownExcerpt(props.suggestion.original_text)),
)
const isWarning = computed(() => props.suggestion.type === 'warning')
const isNewInformation = computed(() =>
  ['addition', 'missing_information'].includes(props.suggestion.type),
)
const confidence = computed(() => {
  const value = props.suggestion.confidence
  if (value >= 0.8) return 'élevée'
  if (value >= 0.5) return 'moyenne'
  return 'faible'
})
const acceptLabel = computed(() =>
  isWarning.value ? "J'ai vu" : isAddition.value ? 'Ajouter' : 'Accepter',
)
const rejectLabel = computed(() => (isAddition.value || isWarning.value ? 'Ignorer' : 'Refuser'))

async function accept(occurrence?: number): Promise<void> {
  busy.value = true
  error.value = ''
  try {
    const result = await api.acceptSuggestion(props.suggestion.id, occurrence)
    emit('decided', props.suggestion.id, isWarning.value ? null : result.course)
  } catch (e) {
    if (e instanceof ApiError && e.code === 'suggestion_ambiguous') {
      occurrences.value = (e.details?.occurrences as Occurrence[] | undefined) ?? []
    } else if (e instanceof ApiError && e.code === 'suggestion_outdated') {
      outdated.value = true
    } else {
      error.value = errorMessage(e)
    }
  } finally {
    busy.value = false
  }
}

async function reject(): Promise<void> {
  busy.value = true
  error.value = ''
  try {
    await api.rejectSuggestion(props.suggestion.id)
    emit('decided', props.suggestion.id, null)
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <article
    class="suggestion"
    :class="suggestion.type"
    :aria-label="label.title"
    :data-suggestion-id="suggestion.id"
  >
    <div class="suggestion-head">
      <h4><component :is="label.icon" :size="18" aria-hidden="true" /> {{ label.title }}</h4>
      <button v-if="anchored" type="button" class="link" @click="emit('show')">
        <Crosshair :size="15" aria-hidden="true" /> Voir dans le cours
      </button>
    </div>

    <template v-if="isAddition">
      <p v-if="suggestion.original_text" class="suggestion-label">
        À ajouter après «
        <!-- eslint-disable-next-line vue/no-v-html -- markdown-it (html: false) -->
        <span class="excerpt" v-html="afterExcerpt" /> » :
      </p>
      <blockquote class="proposed">
        <MarkdownContent :source="suggestion.suggested_text" />
      </blockquote>
    </template>
    <template v-else>
      <blockquote v-if="suggestion.original_text" class="before" aria-label="Dans ton cours">
        <MarkdownContent :source="suggestion.original_text" />
      </blockquote>
      <blockquote v-if="suggestion.suggested_text" class="proposed" aria-label="Proposition">
        <MarkdownContent :source="suggestion.suggested_text" />
      </blockquote>
    </template>

    <p class="suggestion-reason">{{ suggestion.reason }}</p>

    <p v-if="suggestion.source_reference" class="source">
      <BookMarked :size="15" aria-hidden="true" /> D'après : {{ suggestion.source_reference }}
    </p>
    <!-- Moins de texte à lire : la confiance n'est signalée que si elle est faible. -->
    <p v-if="isNewInformation || confidence === 'faible'" class="hint">
      <template v-if="isNewInformation">Pas dans tes notes</template>
      <template v-if="isNewInformation && confidence === 'faible'"> · </template>
      <template v-if="confidence === 'faible'">L'IA n'en est pas sûre</template>
    </p>

    <div v-if="outdated" class="message warning" role="status">
      <p>
        <strong>Le passage visé n'existe plus dans le cours.</strong> Tu peux recopier la suggestion
        à la main si elle est utile :
      </p>
      <pre class="copy-text">{{ suggestion.suggested_text }}</pre>
      <button type="button" @click="emit('decided', suggestion.id, null)">Fermer</button>
    </div>

    <div
      v-else-if="occurrences.length"
      class="occurrences"
      role="group"
      aria-label="Choisis le passage"
    >
      <p><strong>Ce passage apparaît plusieurs fois.</strong> Lequel faut-il modifier ?</p>
      <button
        v-for="occurrence in occurrences"
        :key="occurrence.index"
        type="button"
        class="occurrence"
        :disabled="busy"
        @click="accept(occurrence.index)"
      >
        …{{ occurrence.before }}<mark>{{ occurrence.match }}</mark
        >{{ occurrence.after }}…
      </button>
      <button type="button" class="link" @click="occurrences = []">Annuler</button>
    </div>

    <div v-else class="actions">
      <button type="button" class="primary" :disabled="busy" @click="accept()">
        {{ acceptLabel }}
      </button>
      <button type="button" :disabled="busy" @click="reject">{{ rejectLabel }}</button>
    </div>

    <p v-if="error" class="message error" role="alert">{{ error }}</p>
  </article>
</template>
