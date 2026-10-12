<script setup lang="ts">
import { Download } from 'lucide-vue-next'
import { ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '../api/client'
import { errorMessage } from '../api/errors'
import type { Quiz, RevisionSheet } from '../api/types'
import AiProgress from './AiProgress.vue'
import MarkdownContent from './MarkdownContent.vue'
import QuizPlayer from './QuizPlayer.vue'

const props = defineProps<{ chapterId: number; courseVersion: number }>()

const sheet = ref<RevisionSheet | null>(null)
const quiz = ref<Quiz | null>(null)
const busy = ref<'sheet' | 'quiz' | null>(null)
const error = ref('')

async function load(): Promise<void> {
  try {
    ;[sheet.value, quiz.value] = await Promise.all([
      api.revisionSheet(props.chapterId),
      api.quiz(props.chapterId),
    ])
  } catch (e) {
    error.value = errorMessage(e)
  }
}

// Une nouvelle version du cours peut rendre la fiche et le quiz obsolètes.
watch(() => [props.chapterId, props.courseVersion], load, { immediate: true })

async function createSheet(): Promise<void> {
  busy.value = 'sheet'
  error.value = ''
  try {
    sheet.value = await api.createRevisionSheet(props.chapterId)
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    busy.value = null
  }
}

async function createQuiz(): Promise<void> {
  busy.value = 'quiz'
  error.value = ''
  try {
    quiz.value = await api.createQuiz(props.chapterId)
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    busy.value = null
  }
}
</script>

<template>
  <section class="card" aria-labelledby="study-title">
    <h2 id="study-title">Réviser</h2>
    <p class="hint">La fiche et le quiz sont tirés uniquement de ton cours, sans rien ajouter.</p>
    <p v-if="error" class="message error" role="alert">{{ error }}</p>

    <div class="section-header">
      <h3>Fiche de révision</h3>
      <div class="toolbar">
        <RouterLink
          v-if="sheet"
          class="button-link secondary"
          :to="{ name: 'print', params: { id: chapterId }, query: { quoi: 'fiche' } }"
          target="_blank"
        >
          Imprimer / PDF
        </RouterLink>
        <button type="button" class="primary" :disabled="busy !== null" @click="createSheet">
          {{ sheet ? 'Refaire la fiche' : 'Créer une fiche de révision' }}
        </button>
      </div>
    </div>
    <AiProgress
      operation="revision_sheet"
      :running="busy === 'sheet'"
      title="Création de la fiche de révision"
    />
    <template v-if="sheet">
      <p v-if="sheet.outdated" class="message warning" role="status">
        ⚠ Le cours a changé depuis cette fiche (version {{ sheet.course_version }}) : pense à la
        refaire.
      </p>
      <MarkdownContent class="sheet" :source="sheet.content_markdown" />
    </template>

    <div class="section-header quiz-header">
      <h3>Quiz</h3>
      <button type="button" class="primary" :disabled="busy !== null" @click="createQuiz">
        {{ quiz ? 'Nouveau quiz' : 'Créer un quiz' }}
      </button>
    </div>
    <AiProgress operation="quiz" :running="busy === 'quiz'" title="Création du quiz" />
    <template v-if="quiz">
      <p v-if="quiz.outdated" class="message warning" role="status">
        ⚠ Le cours a changé depuis ce quiz : tu peux en créer un nouveau.
      </p>
      <QuizPlayer :questions="quiz.questions" />
      <div class="anki">
        <a class="button-like" :href="api.quizAnkiUrl(chapterId)" download>
          <Download :size="18" aria-hidden="true" /> Exporter le quiz pour Anki
        </a>
        <p class="hint">
          Pour réviser avec l’application Anki : ouvrez Anki, puis Fichier → Importer, et choisissez
          ce fichier. Chaque question devient une carte.
        </p>
      </div>
    </template>
  </section>
</template>

<style scoped>
.anki {
  margin-top: 1.25rem;
  display: grid;
  gap: 0.5rem;
  justify-items: start;
}
.anki .hint {
  margin: 0;
}
</style>
