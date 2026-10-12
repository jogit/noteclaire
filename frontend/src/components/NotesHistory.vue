<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api/client'
import { errorMessage } from '../api/errors'
import type { NoteVersion, NoteVersionContent, NoteVersionReason } from '../api/types'
import { timeAgo } from '../lib/time'

const props = defineProps<{ chapterId: number; restoring: boolean }>()
const emit = defineEmits<{ restore: [versionId: number]; close: [] }>()

const REASONS: Record<NoteVersionReason, string> = {
  auto: 'Sauvegarde automatique',
  photo: 'Juste après l’import d’une photo',
  structure: 'Au moment de la mise au propre',
  before_restore: 'Avant de remettre une ancienne version',
  big_deletion: 'Avant un gros effacement',
}

const versions = ref<NoteVersion[]>([])
const selected = ref<NoteVersionContent>()
const loading = ref(true)
const error = ref('')

const dateFormat = new Intl.DateTimeFormat('fr-FR', { dateStyle: 'medium', timeStyle: 'short' })

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    versions.value = await api.noteVersions(props.chapterId)
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

async function show(versionId: number): Promise<void> {
  error.value = ''
  try {
    selected.value = await api.noteVersion(props.chapterId, versionId)
  } catch (e) {
    error.value = errorMessage(e)
  }
}

onMounted(load)
defineExpose({ reload: load })
</script>

<template>
  <section class="notes-history" aria-labelledby="notes-history-title">
    <div class="section-header">
      <h3 id="notes-history-title">Anciennes versions de mes notes</h3>
      <button type="button" class="ghost" @click="emit('close')">Fermer</button>
    </div>
    <p class="hint">
      NoteClaire garde une copie de tes notes régulièrement, après chaque photo importée et avant
      chaque mise au propre. Remettre une ancienne version ne perd rien : tes notes actuelles sont
      gardées ici.
    </p>
    <p v-if="error" class="message error" role="alert">{{ error }}</p>
    <p v-else-if="loading" class="hint">Chargement…</p>
    <p v-else-if="!versions.length" class="empty-hint">
      Pas encore d’ancienne version : elles apparaîtront au fil de ton travail.
    </p>

    <div v-else class="notes-history-body">
      <ol class="version-list">
        <li v-for="version in versions" :key="version.id">
          <button
            type="button"
            :aria-pressed="selected?.id === version.id"
            :title="dateFormat.format(new Date(version.created_at))"
            @click="show(version.id)"
          >
            <span class="version-line">
              <strong>{{ timeAgo(version.created_at) }}</strong>
              {{ ' ' }}
              <span class="hint">— {{ REASONS[version.reason] }}, {{ version.words }} mots</span>
            </span>
            <span class="version-preview-text">{{ version.preview }}</span>
          </button>
        </li>
      </ol>

      <div v-if="selected" class="card version-preview" aria-live="polite">
        <div class="section-header">
          <h4>{{ dateFormat.format(new Date(selected.created_at)) }}</h4>
          <button
            type="button"
            class="primary"
            :disabled="restoring"
            @click="emit('restore', selected.id)"
          >
            Remettre cette version
          </button>
        </div>
        <pre class="notes-version-text">{{ selected.raw_text }}</pre>
      </div>
    </div>
  </section>
</template>
