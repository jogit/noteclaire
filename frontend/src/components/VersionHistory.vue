<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api/client'
import { errorMessage } from '../api/errors'
import type { CourseOrigin, CourseVersion, CourseVersionContent } from '../api/types'
import MarkdownContent from './MarkdownContent.vue'

const props = defineProps<{ chapterId: number; currentVersion: number; restoring: boolean }>()
const emit = defineEmits<{ restore: [content: string] }>()

const ORIGINS: Record<CourseOrigin, string> = {
  ai_structure: 'Mise au propre',
  user_edit: 'Modifié à la main',
  suggestion_applied: 'Suggestion acceptée',
}

const versions = ref<CourseVersion[]>([])
const selected = ref<CourseVersionContent>()
const error = ref('')

const dateFormat = new Intl.DateTimeFormat('fr-FR', { dateStyle: 'medium', timeStyle: 'short' })

onMounted(async () => {
  try {
    versions.value = await api.versions(props.chapterId)
  } catch (e) {
    error.value = errorMessage(e)
  }
})

async function show(version: number): Promise<void> {
  error.value = ''
  try {
    selected.value = await api.version(props.chapterId, version)
  } catch (e) {
    error.value = errorMessage(e)
  }
}
</script>

<template>
  <div class="history">
    <p v-if="error" class="message error" role="alert">{{ error }}</p>
    <ol class="version-list">
      <li v-for="version in versions" :key="version.version">
        <button
          type="button"
          :aria-pressed="selected?.version === version.version"
          @click="show(version.version)"
        >
          <strong>Version {{ version.version }}</strong>
          <span v-if="version.version === currentVersion"> (actuelle)</span>
          — {{ ORIGINS[version.origin] }}
          <span class="hint">{{ dateFormat.format(new Date(version.created_at)) }}</span>
        </button>
      </li>
    </ol>

    <section v-if="selected" class="card version-preview" aria-live="polite">
      <div class="section-header">
        <h3>Version {{ selected.version }}</h3>
        <button
          v-if="selected.version !== currentVersion"
          type="button"
          class="secondary"
          :disabled="restoring"
          @click="emit('restore', selected.content_markdown)"
        >
          Restaurer cette version
        </button>
      </div>
      <p v-if="selected.version !== currentVersion" class="hint">
        Restaurer crée une nouvelle version : rien n'est effacé.
      </p>
      <MarkdownContent :source="selected.content_markdown" />
    </section>
  </div>
</template>
