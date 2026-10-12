<script setup lang="ts">
import { Sparkles } from 'lucide-vue-next'
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import {
  type AiOperation,
  estimatedProgress,
  expectedSeconds,
  refreshDurations,
  STAGES,
  stageIndex,
} from '../lib/aiProgress'

/** Barre de progression estimée d'un appel IA, affichée tant que `running` est vrai. */
const props = defineProps<{ operation: AiOperation; running: boolean; title?: string }>()

const visible = ref(false)
const progress = ref(0)
const elapsed = ref(0)
const expected = ref(0)
let timer: ReturnType<typeof setInterval> | undefined
let hideTimer: ReturnType<typeof setTimeout> | undefined
let startedAt = 0

const percent = computed(() => Math.round(progress.value * 100))
const stages = computed(() => STAGES[props.operation])
const stage = computed(() => stages.value[stageIndex(progress.value, stages.value.length)])
const remaining = computed(() => {
  if (progress.value >= 1) return 'Terminé'
  const left = Math.round(expected.value - elapsed.value)
  if (left <= 2) return 'Presque fini…'
  return left >= 60 ? `Environ ${Math.round(left / 60)} min` : `Environ ${left} s`
})

function tick(): void {
  elapsed.value = (performance.now() - startedAt) / 1000
  progress.value = estimatedProgress(elapsed.value, expected.value)
}

async function start(): Promise<void> {
  clearTimeout(hideTimer)
  clearInterval(timer)
  visible.value = true
  progress.value = 0
  elapsed.value = 0
  startedAt = performance.now()
  expected.value = await expectedSeconds(props.operation)
  if (!props.running) return
  timer = setInterval(tick, 200)
}

function finish(): void {
  clearInterval(timer)
  timer = undefined
  if (!visible.value) return
  progress.value = 1
  refreshDurations() // la durée de cet appel compte pour les prochaines estimations
  hideTimer = setTimeout(() => (visible.value = false), 600)
}

watch(
  () => props.running,
  (running) => (running ? start() : finish()),
  { immediate: true },
)

onBeforeUnmount(() => {
  clearInterval(timer)
  clearTimeout(hideTimer)
})
</script>

<template>
  <div v-if="visible" class="ai-progress" :class="{ done: progress >= 1 }">
    <div class="ai-progress-head">
      <span class="ai-progress-icon" aria-hidden="true"><Sparkles :size="18" /></span>
      <strong>{{ title ?? 'L’IA travaille' }}</strong>
      <span class="ai-progress-percent" aria-hidden="true">{{ percent }} %</span>
    </div>
    <div
      class="ai-progress-track"
      role="progressbar"
      :aria-label="title ?? 'Progression estimée'"
      aria-valuemin="0"
      aria-valuemax="100"
      :aria-valuenow="percent"
      :aria-valuetext="`${percent} % (estimation), ${stage}`"
    >
      <span class="ai-progress-fill" :style="{ transform: `scaleX(${progress})` }" />
    </div>
    <div class="ai-progress-foot">
      <span aria-live="polite">{{ stage }}…</span>
      <span class="hint">{{ remaining }}</span>
    </div>
  </div>
</template>
