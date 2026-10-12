<script setup lang="ts">
import { NotebookPen, Plus, Sparkles, Wand2 } from 'lucide-vue-next'
import { computed, inject, onMounted, ref } from 'vue'
import { api } from '../api/client'
import { errorMessage } from '../api/errors'
import type { Chapter } from '../api/types'
import ChapterCard from '../components/ChapterCard.vue'
import SubjectCard from '../components/SubjectCard.vue'
import UsageInfo from '../components/UsageInfo.vue'
import { useSubjects } from '../stores/subjects'

const openNewChapter = inject<(subjectId?: number) => void>('openNewChapter', () => {})
const { subjects, refresh } = useSubjects()

const chapters = ref<Chapter[]>([])
const loading = ref(true)
const error = ref('')

const recent = computed(() => chapters.value.slice(0, 6))
const toReview = computed(
  () =>
    chapters.value.filter(
      (c) => c.progress && c.progress.notes_words > 0 && c.progress.course_version === null,
    ).length,
)

// Les matières sans chapitre se replient dès que l'élève a commencé : l'accueil reste court.
const usedSubjects = computed(() => subjects.value.filter((s) => s.chapter_count))
const unusedSubjects = computed(() => subjects.value.filter((s) => !s.chapter_count))
const foldUnused = computed(() => usedSubjects.value.length > 0 && unusedSubjects.value.length > 0)

const greeting = computed(() => {
  const hour = new Date().getHours()
  return hour < 18 ? 'Bonjour !' : 'Bonsoir !'
})

onMounted(async () => {
  try {
    ;[chapters.value] = await Promise.all([api.chapters(), refresh()])
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <section class="hero">
    <div>
      <h1>{{ greeting }}</h1>
      <p v-if="toReview">
        {{ toReview }} chapitre{{ toReview > 1 ? 's attendent' : ' attend' }} d’être mis au propre.
      </p>
      <p v-else>Prêt à remettre tes notes au propre ?</p>
    </div>
    <button type="button" class="primary" @click="openNewChapter()">
      <Plus :size="20" aria-hidden="true" /> Nouveau chapitre
    </button>
  </section>

  <p v-if="error" class="message error" role="alert">{{ error }}</p>

  <template v-if="!loading && !chapters.length && !error">
    <div class="empty-state">
      <Sparkles :size="36" aria-hidden="true" />
      <strong>Bienvenue dans NoteClaire</strong>
      <span>Ton premier cours propre en trois étapes :</span>
      <div class="steps">
        <div class="step"><b>1. Tes notes</b>Tape ou photographie tes notes de cours.</div>
        <div class="step"><b>2. Au propre</b>L’IA les met en forme sans rien inventer.</div>
        <div class="step"><b>3. Réviser</b>Suggestions, fiche de révision et quiz.</div>
      </div>
      <button type="button" class="primary" @click="openNewChapter()">
        <NotebookPen :size="20" aria-hidden="true" /> Créer mon premier chapitre
      </button>
    </div>
  </template>

  <template v-if="recent.length">
    <div class="section-header">
      <h2>Reprendre</h2>
    </div>
    <div class="card-grid">
      <ChapterCard v-for="chapter in recent" :key="chapter.id" :chapter="chapter" show-subject />
    </div>
  </template>

  <h2>Mes matières</h2>
  <div class="card-grid">
    <SubjectCard
      v-for="subject in foldUnused ? usedSubjects : subjects"
      :key="subject.id"
      :subject="subject"
    />
  </div>
  <details v-if="foldUnused" class="other-subjects">
    <summary>Autres matières ({{ unusedSubjects.length }})</summary>
    <div class="card-grid">
      <SubjectCard v-for="subject in unusedSubjects" :key="subject.id" :subject="subject" />
    </div>
  </details>

  <div class="hint usage-line">
    <Wand2 :size="16" aria-hidden="true" />
    <UsageInfo />
  </div>
</template>

<style scoped>
.usage-line {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin-top: 2rem;
}

.usage-line :deep(.usage) {
  margin: 0;
}
</style>
