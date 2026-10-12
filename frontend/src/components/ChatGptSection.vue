<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api/client'
import { errorMessage, messageForCode } from '../api/errors'
import ChatGptHostNotice from './ChatGptHostNotice.vue'
import type { ChatGPTModel, ChatGPTStatus } from '../api/types'
import { CHATGPT_USAGE_URL, canSignInHere } from '../lib/chatgptHost'

const route = useRoute()
const router = useRouter()

const status = ref<ChatGPTStatus>()
const models = ref<ChatGPTModel[]>([])
const selectedModel = ref('')
const busy = ref(false)
const error = ref('')
const message = ref('')

async function load(): Promise<void> {
  try {
    status.value = await api.chatgptStatus()
    selectedModel.value = status.value.model
    models.value = status.value.connected ? await api.chatgptModels() : []
  } catch (e) {
    error.value = errorMessage(e)
  }
}

onMounted(async () => {
  // Retour de la connexion sur chatgpt.com : le serveur ajoute ?chatgpt=connecte ou erreur.
  const result = route.query.chatgpt
  if (result === 'connecte') message.value = 'Votre compte ChatGPT est connecté.'
  if (result === 'erreur') error.value = messageForCode(String(route.query.code ?? ''))
  if (result) router.replace({ query: { onglet: 'ia' } })
  await load()
})

async function signIn(): Promise<void> {
  busy.value = true
  error.value = ''
  try {
    const { authorization_url } = await api.chatgptLogin()
    window.location.assign(authorization_url)
  } catch (e) {
    error.value = errorMessage(e)
    busy.value = false
  }
}

async function saveModel(): Promise<void> {
  error.value = ''
  message.value = ''
  try {
    await api.chatgptSetModel(selectedModel.value)
    message.value = 'Modèle enregistré.'
  } catch (e) {
    error.value = errorMessage(e)
  }
}

async function signOut(): Promise<void> {
  if (!window.confirm('Déconnecter votre compte ChatGPT de NoteClaire ?')) return
  busy.value = true
  error.value = ''
  message.value = ''
  try {
    const { revoked } = await api.chatgptLogout()
    message.value = revoked
      ? 'Compte ChatGPT déconnecté.'
      : 'Déconnecté ici, mais la révocation côté ChatGPT n’a pas pu être confirmée : ' +
        'retirez NoteClaire dans les réglages de ChatGPT.'
    await load()
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <section v-if="status?.ai_provider === 'chatgpt'" class="card" aria-labelledby="chatgpt-title">
    <h2 id="chatgpt-title">Compte ChatGPT</h2>
    <p v-if="message" class="message success" role="status">{{ message }}</p>
    <p v-if="error" class="message error" role="alert">{{ error }}</p>

    <template v-if="status.connected">
      <p>
        ✔ Connecté : <strong>{{ status.name || status.email }}</strong>
        <span v-if="status.name && status.email" class="hint"> ({{ status.email }})</span>
      </p>
      <div v-if="models.length" class="model-choice">
        <label for="chatgpt-model">Modèle utilisé</label>
        <div class="row">
          <select id="chatgpt-model" v-model="selectedModel">
            <option v-if="!selectedModel" value="">Premier modèle proposé</option>
            <option v-for="model in models" :key="model.slug" :value="model.slug">
              {{ model.display_name }}
            </option>
          </select>
          <button type="button" class="secondary" @click="saveModel">Enregistrer</button>
        </div>
      </div>
      <p class="hint">
        Using ChatGPT plan ·
        <a :href="CHATGPT_USAGE_URL" target="_blank" rel="noopener noreferrer">Manage usage</a>
        : la consommation de NoteClaire se limite dans les réglages de ChatGPT.
      </p>
      <button type="button" class="danger" :disabled="busy" @click="signOut">Se déconnecter</button>
    </template>

    <template v-else>
      <p v-if="status.needs_reauth" class="message warning">
        La connexion a expiré ou a été retirée : reconnectez-vous.
      </p>
      <p>
        Connectez votre abonnement ChatGPT Plus ou Pro : vous serez envoyé sur chatgpt.com pour
        autoriser NoteClaire, puis ramené ici. Ensuite, tous les appareils de la maison utilisent
        l’IA.
      </p>
      <button v-if="canSignInHere()" type="button" class="primary" :disabled="busy" @click="signIn">
        Continue with ChatGPT
      </button>
      <ChatGptHostNotice v-else />
    </template>
  </section>
</template>
