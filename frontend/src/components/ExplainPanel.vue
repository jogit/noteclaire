<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api/client'
import { errorMessage } from '../api/errors'
import type { ExplainMode, Explanation } from '../api/types'
import { markdownExcerpt, renderInlineMarkdown } from '../lib/markdown'
import AiProgress from './AiProgress.vue'
import MarkdownContent from './MarkdownContent.vue'

/**
 * « Je n'ai pas compris » : une fenêtre au centre, qui met le cours en retrait.
 * Une seule chose à lire : l'explication (courte), puis « J'ai compris ».
 */
const props = defineProps<{ chapterId: number; passage: string }>()
const emit = defineEmits<{ close: [] }>()

const MODES: { mode: ExplainMode; label: string }[] = [
  { mode: 'simpler', label: 'Autrement' },
  { mode: 'example', label: 'Un exemple' },
  { mode: 'question', label: 'Une question' },
]

const dialog = ref<HTMLDialogElement>()
const result = ref<Explanation>()
const showAnswer = ref(false)
const busy = ref(false)
const error = ref('')
const quote = renderInlineMarkdown(markdownExcerpt(props.passage, 120))

// Un clic sur « Je n'ai pas compris » suffit : la première explication arrive tout de suite.
onMounted(() => {
  dialog.value?.showModal?.()
  ask('simpler')
})

async function ask(mode: ExplainMode): Promise<void> {
  busy.value = true
  error.value = ''
  showAnswer.value = false
  try {
    result.value = await api.explain(props.chapterId, props.passage, mode)
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    busy.value = false
  }
}

function close(): void {
  dialog.value?.close?.()
  emit('close')
}
</script>

<template>
  <dialog
    ref="dialog"
    class="explain"
    aria-labelledby="explain-title"
    @cancel.prevent="close"
    @click.self="close"
  >
    <h2 id="explain-title">Je n'ai pas compris</h2>
    <!-- eslint-disable-next-line vue/no-v-html -- markdown-it (html: false) -->
    <p class="explain-quote">« <span v-html="quote" /> »</p>

    <AiProgress operation="explain" :running="busy" title="L’IA cherche une explication" />
    <p v-if="error" class="message error" role="alert">{{ error }}</p>

    <div v-if="result && !busy" class="explain-result" aria-live="polite">
      <MarkdownContent :source="result.text" />
      <template v-if="result.answer">
        <button v-if="!showAnswer" type="button" class="secondary" @click="showAnswer = true">
          Voir la réponse
        </button>
        <MarkdownContent v-else class="explain-answer" :source="result.answer" />
      </template>
    </div>

    <div class="explain-actions">
      <button type="button" class="primary" @click="close">J'ai compris</button>
      <span class="explain-more">
        <span class="hint">Encore :</span>
        <button
          v-for="option in MODES"
          :key="option.mode"
          type="button"
          class="ghost"
          :disabled="busy"
          @click="ask(option.mode)"
        >
          {{ option.label }}
        </button>
      </span>
    </div>
    <p class="hint explain-note">Explication de l'IA : elle n'est pas ajoutée à ton cours.</p>
  </dialog>
</template>
