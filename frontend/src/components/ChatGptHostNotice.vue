<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../api/client'

const redirectUri = ref('')

// L'adresse vient du serveur : elle suit le port choisi (HTTP_PORT).
const address = computed(() => {
  try {
    return new URL(redirectUri.value).origin
  } catch {
    return 'http://127.0.0.1'
  }
})

onMounted(async () => {
  try {
    redirectUri.value = (await api.chatgptStatus()).redirect_uri
  } catch {
    // L'adresse par défaut suffit à expliquer quoi faire.
  }
})
</script>

<template>
  <p class="message info" role="status">
    <span>
      Pour connecter ChatGPT, ouvrez NoteClaire sur l’ordinateur qui l’héberge, à l’adresse
      <code>{{ address }}</code> (pas <code>localhost</code>) : OpenAI ne renvoie que vers cette
      adresse locale. Cela se fait une seule fois, ensuite tous les appareils de la maison utilisent
      l’IA.
    </span>
  </p>
</template>
