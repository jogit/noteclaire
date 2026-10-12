<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api/client'

const version = ref('')

onMounted(async () => {
  try {
    version.value = (await api.appVersion()).version
  } catch {
    // Information facultative : sans réponse du serveur, rien n'est affiché.
  }
})
</script>

<template>
  <p v-if="version" class="hint">NoteClaire, version {{ version }}</p>
</template>
