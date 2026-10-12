<script setup lang="ts">
import { RotateCcw, Trash2 } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api/client'
import { errorMessage } from '../api/errors'
import type { TrashItem } from '../api/types'
import { timeAgo } from '../lib/time'
import { useSubjects } from '../stores/subjects'

const router = useRouter()
const { refresh: refreshSubjects } = useSubjects()

const items = ref<TrashItem[]>([])
const loading = ref(true)
const busy = ref<number>()
const error = ref('')

const dayFormat = new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'long' })

async function load(): Promise<void> {
  error.value = ''
  try {
    items.value = await api.trash()
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

async function restore(item: TrashItem): Promise<void> {
  busy.value = item.id
  error.value = ''
  try {
    await api.restoreChapter(item.id)
    refreshSubjects().catch(() => {})
    await router.push({ name: 'chapter', params: { id: item.id } })
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    busy.value = undefined
  }
}

async function purge(item: TrashItem): Promise<void> {
  const confirmed = window.confirm(
    `Effacer définitivement « ${item.title} » ? Les notes, le cours, les fiches et les images ` +
      'de ce chapitre ne pourront plus être récupérés.',
  )
  if (!confirmed) return
  busy.value = item.id
  error.value = ''
  try {
    await api.purgeChapter(item.id)
    items.value = items.value.filter((i) => i.id !== item.id)
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    busy.value = undefined
  }
}

onMounted(load)
</script>

<template>
  <h1>Corbeille</h1>
  <p>
    Les chapitres supprimés restent ici 30 jours. Tu peux les récupérer tels quels : notes, cours,
    versions, fiches et images.
  </p>

  <p v-if="error" class="message error" role="alert">{{ error }}</p>

  <section class="card">
    <p v-if="loading" class="hint">Chargement…</p>
    <p v-else-if="!items.length" class="empty-hint">La corbeille est vide.</p>
    <ul v-else class="item-list">
      <li v-for="item in items" :key="item.id">
        <div>
          <strong>{{ item.title }}</strong>
          <span class="chapter-subject">
            {{ item.subject.name }} — supprimé {{ timeAgo(item.deleted_at) }}, effacé le
            {{ dayFormat.format(new Date(item.expires_at)) }}
          </span>
        </div>
        <div class="actions">
          <button type="button" class="primary" :disabled="busy === item.id" @click="restore(item)">
            <RotateCcw :size="18" aria-hidden="true" /> Récupérer
          </button>
          <button
            type="button"
            class="ghost"
            :disabled="busy === item.id"
            :aria-label="`Effacer définitivement ${item.title}`"
            @click="purge(item)"
          >
            <Trash2 :size="18" aria-hidden="true" /> Effacer
          </button>
        </div>
      </li>
    </ul>
  </section>
</template>
