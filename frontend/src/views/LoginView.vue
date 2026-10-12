<script setup lang="ts">
import { Sparkles } from 'lucide-vue-next'
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api/client'
import { errorMessage } from '../api/errors'

const route = useRoute()
const router = useRouter()
const password = ref('')
const error = ref('')
const busy = ref(false)

async function submit(): Promise<void> {
  busy.value = true
  error.value = ''
  try {
    await api.login(password.value)
    const next = typeof route.query.suite === 'string' ? route.query.suite : '/'
    await router.replace(next.startsWith('/') ? next : '/')
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <section class="card narrow">
    <p class="login-brand"><Sparkles :size="22" aria-hidden="true" /> NoteClaire</p>
    <h1>Connexion</h1>
    <form @submit.prevent="submit">
      <label for="password">Mot de passe</label>
      <input
        id="password"
        v-model="password"
        type="password"
        autocomplete="current-password"
        required
      />
      <p v-if="error" class="message error" role="alert">{{ error }}</p>
      <button type="submit" class="primary" :disabled="busy">Se connecter</button>
    </form>
  </section>
</template>

<style scoped>
.login-brand {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0 1rem;
  font-weight: 700;
  color: var(--primary);
}

form .primary {
  margin-top: 1rem;
  width: 100%;
}
</style>
