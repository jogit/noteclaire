<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { QuizQuestion } from '../api/types'
import MarkdownContent from './MarkdownContent.vue'

const props = defineProps<{ questions: QuizQuestion[] }>()

const index = ref(0)
const selected = ref<string | null>(null)
const shortAnswer = ref('')
const revealed = ref(false)
const correct = ref<boolean | null>(null)
const score = ref(0)
const finished = ref(false)

const question = computed(() => props.questions[index.value]!)
const isLast = computed(() => index.value === props.questions.length - 1)

function reset(): void {
  index.value = 0
  score.value = 0
  finished.value = false
  resetQuestion()
}

function resetQuestion(): void {
  selected.value = null
  shortAnswer.value = ''
  revealed.value = false
  correct.value = null
}

watch(() => props.questions, reset)

function choose(choice: string): void {
  if (revealed.value) return
  selected.value = choice
  revealed.value = true
  correct.value = choice === question.value.answer
  if (correct.value) score.value++
}

/** Réponse courte : l'élève compare lui-même avec la réponse attendue. */
function selfAssess(right: boolean): void {
  correct.value = right
  if (right) score.value++
}

function next(): void {
  if (isLast.value) {
    finished.value = true
    return
  }
  index.value++
  resetQuestion()
}
</script>

<template>
  <div class="quiz">
    <template v-if="!finished">
      <p class="hint">Question {{ index + 1 }} sur {{ questions.length }}</p>
      <div class="quiz-question"><MarkdownContent :source="question.question" /></div>

      <div v-if="question.type !== 'short'" class="quiz-choices" role="group" aria-label="Réponses">
        <button
          v-for="choice in question.choices"
          :key="choice"
          type="button"
          class="quiz-choice"
          :class="{
            right: revealed && choice === question.answer,
            wrong: revealed && choice === selected && choice !== question.answer,
          }"
          :aria-pressed="choice === selected"
          :disabled="revealed"
          @click="choose(choice)"
        >
          <MarkdownContent :source="choice" />
          <span v-if="revealed && choice === question.answer" class="badge">✔ Bonne réponse</span>
          <span v-else-if="revealed && choice === selected" class="badge">✘ Ta réponse</span>
        </button>
      </div>

      <form v-else class="quiz-short" @submit.prevent="revealed = true">
        <label for="short-answer">Ta réponse</label>
        <input
          id="short-answer"
          v-model="shortAnswer"
          type="text"
          autocomplete="off"
          :disabled="revealed"
        />
        <button v-if="!revealed" type="submit" class="primary">Voir la réponse</button>
        <template v-else>
          <p><strong>Réponse attendue :</strong></p>
          <MarkdownContent :source="question.answer" />
          <div v-if="correct === null" class="actions">
            <button type="button" class="primary" @click="selfAssess(true)">✔ J'avais juste</button>
            <button type="button" @click="selfAssess(false)">✘ Je m'étais trompé</button>
          </div>
        </template>
      </form>

      <div v-if="correct !== null" class="quiz-feedback" role="status">
        <p class="quiz-verdict">{{ correct ? '✔ Bravo !' : '✘ Pas tout à fait.' }}</p>
        <MarkdownContent :source="question.explanation" />
        <template v-if="question.course_excerpt">
          <p class="suggestion-label">Dans ton cours :</p>
          <blockquote><MarkdownContent :source="question.course_excerpt" /></blockquote>
        </template>
        <button type="button" class="primary" @click="next">
          {{ isLast ? 'Voir mon score' : 'Question suivante' }}
        </button>
      </div>
    </template>

    <div v-else class="quiz-result" role="status">
      <p class="quiz-score">Score : {{ score }} / {{ questions.length }}</p>
      <p>
        {{
          score === questions.length
            ? 'Parfait, tu maîtrises ce chapitre !'
            : 'Relis les points où tu t’es trompé, puis recommence.'
        }}
      </p>
      <button type="button" class="primary" @click="reset">Recommencer</button>
    </div>
  </div>
</template>
