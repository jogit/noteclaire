<script setup lang="ts">
import { ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { api } from '../api/client'
import { errorMessage } from '../api/errors'
import type { SearchResult } from '../api/types'

const route = useRoute()
const results = ref<SearchResult[]>([])
const query = ref('')
const loading = ref(false)
const error = ref('')

type Part = { text: string; marked: boolean }

/** Découpe l'extrait selon les repères de surlignage du serveur (sans v-html). */
function highlight(snippet: string): Part[] {
  return snippet
    .split(/(\u0002[^\u0003]*\u0003)/)
    .filter(Boolean)
    .map((part) =>
      part.startsWith('\u0002')
        ? { text: part.slice(1, -1), marked: true }
        : { text: part, marked: false },
    )
}

watch(
  () => route.query.q,
  async (value) => {
    query.value = typeof value === 'string' ? value : ''
    error.value = ''
    if (!query.value.trim()) {
      results.value = []
      return
    }
    loading.value = true
    try {
      results.value = await api.search(query.value)
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
  <h1>Recherche</h1>
  <p v-if="error" class="message error" role="alert">{{ error }}</p>
  <p v-if="loading" aria-live="polite">Recherche…</p>
  <p v-else-if="query && !results.length" role="status">Aucun résultat pour « {{ query }} ».</p>
  <ul class="chapter-list search-results">
    <li v-for="result in results" :key="result.chapter_id">
      <RouterLink :to="{ name: 'chapter', params: { id: result.chapter_id } }">
        <span class="chapter-subject">{{ result.subject }}</span>
        {{ result.title }}
        <span class="snippet">
          <template v-for="(part, index) in highlight(result.snippet)" :key="index">
            <mark v-if="part.marked">{{ part.text }}</mark>
            <template v-else>{{ part.text }}</template>
          </template>
        </span>
      </RouterLink>
    </li>
  </ul>
</template>
