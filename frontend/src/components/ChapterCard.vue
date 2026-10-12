<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import type { Chapter } from '../api/types'
import { subjectStyle, subjectVars } from '../lib/subjects'
import { timeAgo } from '../lib/time'

const props = defineProps<{ chapter: Chapter; showSubject?: boolean }>()

const style = computed(() => subjectStyle(props.chapter.subject.slug))
const progress = computed(() => props.chapter.progress)
</script>

<template>
  <RouterLink
    class="chapter-card"
    :style="subjectVars(chapter.subject.slug)"
    :to="{ name: 'chapter', params: { id: chapter.id } }"
  >
    <div v-if="showSubject" class="chapter-card-head">
      <span class="subject-dot"><component :is="style.icon" :size="16" aria-hidden="true" /></span>
      {{ chapter.subject.name }}
    </div>
    <h3>{{ chapter.title }}</h3>
    <div v-if="progress" class="chips">
      <span v-if="!progress.notes_words" class="chip">Pas encore de notes</span>
      <span v-else-if="progress.course_version === null" class="chip todo">
        À mettre au propre
      </span>
      <span v-else-if="progress.notes_changed" class="chip todo">Notes modifiées</span>
      <span v-else class="chip done">✓ Cours prêt</span>
      <span v-if="progress.pending_suggestions" class="chip info">
        {{ progress.pending_suggestions }} suggestion{{
          progress.pending_suggestions > 1 ? 's' : ''
        }}
      </span>
      <span v-if="progress.has_revision_sheet" class="chip">Fiche</span>
      <span v-if="progress.has_quiz" class="chip">Quiz</span>
    </div>
    <span class="when">Modifié {{ timeAgo(chapter.updated_at) }}</span>
  </RouterLink>
</template>
