<script setup lang="ts">
import { NotebookPen, Plus } from 'lucide-vue-next'
import { computed, inject, ref, watch } from 'vue'
import { api } from '../api/client'
import { errorMessage } from '../api/errors'
import type { Chapter } from '../api/types'
import ChapterCard from '../components/ChapterCard.vue'
import { subjectStyle, subjectVars } from '../lib/subjects'
import { useSubjects } from '../stores/subjects'

const props = defineProps<{ slug: string }>()
const openNewChapter = inject<(subjectId?: number) => void>('openNewChapter', () => {})
const { bySlug, ensureLoaded } = useSubjects()

const chapters = ref<Chapter[]>([])
const loading = ref(true)
const error = ref('')

const subject = computed(() => bySlug(props.slug))
const style = computed(() => subjectStyle(props.slug))

watch(
  () => props.slug,
  async () => {
    loading.value = true
    error.value = ''
    try {
      await ensureLoaded()
      if (!subject.value) {
        error.value = "Cette matière n'existe pas."
        return
      }
      chapters.value = await api.chapters(subject.value.id)
    } catch (e) {
      error.value = errorMessage(e)
    } finally {
      loading.value = false
    }
  },
  { immediate: true },
)
</script>

<template>
  <p v-if="error" class="message error" role="alert">{{ error }}</p>

  <template v-if="subject">
    <section class="subject-banner" :style="subjectVars(slug)">
      <span class="subject-dot"><component :is="style.icon" :size="28" aria-hidden="true" /></span>
      <div class="grow">
        <h1>{{ subject.name }}</h1>
        <p>
          {{
            chapters.length
              ? `${chapters.length} chapitre${chapters.length > 1 ? 's' : ''}`
              : 'Aucun chapitre pour l’instant'
          }}
        </p>
      </div>
      <button type="button" class="primary" @click="openNewChapter(subject.id)">
        <Plus :size="20" aria-hidden="true" /> Nouveau chapitre
      </button>
    </section>

    <div v-if="!loading && !chapters.length" class="empty-state">
      <NotebookPen :size="34" aria-hidden="true" />
      <strong>Pas encore de chapitre en {{ subject.name }}</strong>
      <span>Crée un chapitre pour y ranger tes notes de cours.</span>
      <button type="button" class="primary" @click="openNewChapter(subject.id)">
        <Plus :size="20" aria-hidden="true" /> Nouveau chapitre
      </button>
    </div>

    <div class="card-grid">
      <ChapterCard v-for="chapter in chapters" :key="chapter.id" :chapter="chapter" />
    </div>
  </template>
</template>

<style scoped>
.grow {
  flex: 1;
}

.subject-banner {
  flex-wrap: wrap;
}
</style>
