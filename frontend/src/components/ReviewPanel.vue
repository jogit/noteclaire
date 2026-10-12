<script setup lang="ts">
import { CheckCircle2, Lightbulb, X } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'
import { api } from '../api/client'
import { errorMessage } from '../api/errors'
import type { Course, Suggestion } from '../api/types'
import AiProgress from './AiProgress.vue'
import SuggestionCard from './SuggestionCard.vue'

/**
 * Relecture du cours par l'IA, pensée pour ne pas surcharger l'écran :
 * une barre discrète au-dessus du cours, puis les points un par un dans un panneau en bas.
 * Seul le passage du point affiché est surligné. Rien ne change sans l'accord de l'élève.
 */
const props = defineProps<{ chapterId: number; courseVersion: number; anchored: Set<number> }>()
const emit = defineEmits<{
  'update:course': [course: Course]
  suggestions: [list: Suggestion[]]
  focus: [id: number | null]
}>()

const suggestions = ref<Suggestion[]>([])
const analyzing = ref(false)
const analyzed = ref(false)
const finished = ref(false)
const open = ref(false)
const index = ref(0)
const error = ref('')

const count = computed(() => suggestions.value.length)
const current = computed(() => (open.value ? suggestions.value[index.value] : undefined))

watch(suggestions, (value) => emit('suggestions', value))
watch(current, (value) => emit('focus', value?.id ?? null))

async function loadSuggestions(): Promise<void> {
  try {
    suggestions.value = await api.pendingSuggestions(props.chapterId)
  } catch (e) {
    error.value = errorMessage(e)
  }
}

// Une nouvelle version peut rendre des suggestions obsolètes : on recharge.
watch(() => [props.chapterId, props.courseVersion], loadSuggestions, { immediate: true })

/**
 * Lance une relecture. S'il reste des points non regardés, demande d'abord confirmation
 * (sauf juste après une mise au propre : le cours a changé, ces points ne valent plus).
 */
async function analyze(askFirst = true): Promise<void> {
  if (analyzing.value) return
  if (askFirst && count.value) {
    const plural = count.value > 1
    const confirmed = window.confirm(
      `Il reste ${count.value} point${plural ? 's' : ''} à regarder. ` +
        `Les remplacer par une nouvelle relecture ? Les suggestions déjà acceptées restent ` +
        `dans ton cours, et celles que tu as refusées ne seront pas reproposées.`,
    )
    if (!confirmed) return
  }
  analyzing.value = true
  open.value = false
  finished.value = false
  error.value = ''
  try {
    suggestions.value = await api.analyze(props.chapterId)
    analyzed.value = true
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    analyzing.value = false
  }
}

/** Ouvre la relecture, au premier point ou sur celui dont le passage a été cliqué. */
function start(id?: number): void {
  const found = id === undefined ? -1 : suggestions.value.findIndex((s) => s.id === id)
  index.value = Math.max(0, found)
  finished.value = false
  open.value = count.value > 0
}

function close(): void {
  open.value = false
}

function onDecided(id: number, course: Course | null): void {
  suggestions.value = suggestions.value.filter((s) => s.id !== id)
  if (course) emit('update:course', course)
  if (!suggestions.value.length) {
    open.value = false
    finished.value = true
  } else if (index.value >= suggestions.value.length) {
    index.value = suggestions.value.length - 1
  }
}

function step(delta: number): void {
  index.value = (index.value + delta + count.value) % count.value
}

defineExpose({ analyze, start })
</script>

<template>
  <div class="course-review-bar" :class="{ todo: count && !open }" aria-live="polite">
    <AiProgress operation="analyze" :running="analyzing" title="L'IA relit ton cours" />
    <p v-if="error" class="message error" role="alert">{{ error }}</p>

    <template v-if="!analyzing">
      <template v-if="count">
        <Lightbulb :size="20" aria-hidden="true" />
        <span>
          <strong>{{ count }} point{{ count > 1 ? 's' : '' }}</strong> à regarder dans ton cours
        </span>
        <button v-if="!open" type="button" class="primary" @click="start()">Regarder</button>
        <button v-if="!open" type="button" class="link" @click="analyze()">Relire à nouveau</button>
      </template>
      <template v-else-if="finished || analyzed">
        <CheckCircle2 :size="20" class="ok" aria-hidden="true" />
        <span>{{ finished ? 'Relecture terminée.' : 'Rien à signaler dans ton cours.' }}</span>
        <button type="button" class="link" @click="analyze()">Relire à nouveau</button>
      </template>
      <button v-else type="button" class="secondary" @click="analyze()">
        Faire relire mon cours par l'IA
      </button>
    </template>
  </div>

  <section v-if="current" class="review-sheet" aria-labelledby="review-sheet-title">
    <div class="review-sheet-head">
      <h3 id="review-sheet-title">Point {{ index + 1 }} sur {{ count }}</h3>
      <span class="review-sheet-nav">
        <button v-if="count > 1" type="button" class="ghost" @click="step(1)">Suivant</button>
        <button type="button" class="icon ghost" aria-label="Plus tard" @click="close">
          <X :size="20" aria-hidden="true" />
        </button>
      </span>
    </div>
    <SuggestionCard
      :key="current.id"
      :suggestion="current"
      :anchored="anchored.has(current.id)"
      @decided="onDecided"
      @show="emit('focus', current.id)"
    />
  </section>
</template>
