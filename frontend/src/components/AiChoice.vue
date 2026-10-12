<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api/client'
import { errorMessage } from '../api/errors'
import type { AIProviderChoice } from '../api/types'

const props = defineProps<{ submitLabel?: string }>()
const emit = defineEmits<{ saved: [result: { ok: boolean; message: string; provider: string }] }>()

const CHOICES: { id: AIProviderChoice; label: string; help: string }[] = [
  { id: 'openai', label: 'Clé OpenAI', help: 'Une clé API OpenAI (facturée à l’usage).' },
  { id: 'chatgpt', label: 'Compte ChatGPT', help: 'Un abonnement ChatGPT Plus ou Pro.' },
  { id: 'local', label: 'IA sur mon ordinateur', help: 'Ollama, LM Studio… (gratuit).' },
  { id: 'fake', label: 'Essayer sans IA', help: 'Les notes sont renvoyées telles quelles.' },
]

const provider = ref<AIProviderChoice>('openai')
const apiKey = ref('')
const hasKey = ref(false)
const localUrl = ref('')
const localModel = ref('')
const busy = ref(false)
const error = ref('')

onMounted(async () => {
  try {
    const setup = await api.setupStatus()
    hasKey.value = setup.has_openai_key
    localUrl.value = setup.local_ai_base_url
    localModel.value = setup.local_ai_model
    if (['openai', 'chatgpt', 'local'].includes(setup.ai_provider)) {
      provider.value = setup.ai_provider as AIProviderChoice
    }
  } catch (e) {
    error.value = errorMessage(e)
  }
})

async function save(): Promise<void> {
  busy.value = true
  error.value = ''
  try {
    await api.saveAI({
      ai_provider: provider.value,
      openai_api_key: provider.value === 'openai' ? apiKey.value.trim() : undefined,
      local_ai_base_url: provider.value === 'local' ? localUrl.value.trim() : undefined,
      local_ai_model: provider.value === 'local' ? localModel.value.trim() : undefined,
    })
    apiKey.value = ''
    hasKey.value = hasKey.value || provider.value === 'openai'
    emit('saved', { ...(await api.testAI()), provider: provider.value })
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <form @submit.prevent="save">
    <p v-if="error" class="message error" role="alert">{{ error }}</p>
    <fieldset class="ai-choices">
      <legend class="visually-hidden">Choix de l’IA</legend>
      <label v-for="choice in CHOICES" :key="choice.id" class="choice">
        <input v-model="provider" type="radio" name="provider" :value="choice.id" />
        <span>
          <strong>{{ choice.label }}</strong>
          <span class="hint">{{ choice.help }}</span>
        </span>
      </label>
    </fieldset>

    <template v-if="provider === 'openai'">
      <label for="ai-key">Clé API OpenAI</label>
      <input
        id="ai-key"
        v-model="apiKey"
        type="password"
        autocomplete="off"
        :placeholder="hasKey ? 'Une clé est déjà enregistrée' : 'sk-…'"
        :required="!hasKey"
      />
      <p class="hint">
        Elle est gardée sur votre serveur et n’est jamais affichée ni envoyée ailleurs qu’à OpenAI.
      </p>
    </template>
    <template v-else-if="provider === 'local'">
      <label for="ai-url">Adresse du serveur</label>
      <input id="ai-url" v-model="localUrl" type="text" required />
      <label for="ai-model">Nom du modèle</label>
      <input id="ai-model" v-model="localModel" type="text" required />
    </template>
    <p v-else-if="provider === 'chatgpt'" class="hint">
      Vous serez envoyé sur le site de ChatGPT pour vous connecter, juste après.
    </p>

    <div class="ai-actions">
      <slot name="before-submit" />
      <button type="submit" class="primary" :disabled="busy">
        {{ busy ? 'Vérification…' : (props.submitLabel ?? 'Enregistrer et tester') }}
      </button>
    </div>
  </form>
</template>

<style scoped>
.ai-choices {
  border: 0;
  padding: 0;
  margin: 0 0 1rem;
  display: grid;
  gap: 0.5rem;
}
.choice {
  display: flex;
  gap: 0.75rem;
  align-items: flex-start;
  margin: 0;
  cursor: pointer;
}
.choice .hint {
  display: block;
  margin: 0;
  font-weight: 400;
}
.choice strong {
  display: block;
}
.ai-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: space-between;
  margin-top: 1rem;
}
</style>
