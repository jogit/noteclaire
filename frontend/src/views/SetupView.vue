<script setup lang="ts">
import { Download, Sparkles } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api/client'
import { errorMessage } from '../api/errors'
import AdaptationPicker from '../components/AdaptationPicker.vue'
import AiChoice from '../components/AiChoice.vue'
import ChatGptHostNotice from '../components/ChatGptHostNotice.vue'
import type { Level } from '../api/types'
import { canSignInHere } from '../lib/chatgptHost'
import { markSetupDone } from '../lib/setupState'

const router = useRouter()
const step = ref(1)
const busy = ref(false)
const error = ref('')

const levels = ref<Level[]>([])
const studentId = ref<number>()
const name = ref('')
const level = ref('seconde')
const adaptationNotes = ref('')
const adaptationCodes = ref<string[]>([])

function onAdaptations(value: { codes: string[]; free: string }): void {
  adaptationCodes.value = value.codes
  adaptationNotes.value = value.free
}

const provider = ref('openai')
const testResult = ref<{ ok: boolean; message: string }>()

onMounted(async () => {
  try {
    const [list, students] = await Promise.all([api.levels(), api.students()])
    levels.value = list
    studentId.value = students[0]?.id
    name.value = students[0]?.name === 'Élève' ? '' : (students[0]?.name ?? '')
    level.value = students[0]?.level ?? 'seconde'
    adaptationNotes.value = students[0]?.adaptation_notes ?? ''
    adaptationCodes.value = students[0]?.adaptation_codes ?? []
  } catch (e) {
    error.value = errorMessage(e)
  }
})

async function run(action: () => Promise<void>): Promise<void> {
  busy.value = true
  error.value = ''
  try {
    await action()
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    busy.value = false
  }
}

function saveStudent(): Promise<void> {
  return run(async () => {
    if (studentId.value !== undefined) {
      await api.updateStudent(studentId.value, {
        name: name.value.trim() || 'Élève',
        level: level.value,
        adaptation_codes: adaptationCodes.value,
        adaptation_notes: adaptationNotes.value,
      })
    }
    step.value = 2
  })
}

function onAiSaved(result: { ok: boolean; message: string; provider: string }): void {
  testResult.value = { ok: result.ok, message: result.message }
  provider.value = result.provider
  step.value = 3
}

// Programmes officiels de la classe : proposés ici pour que la relecture cite sa source dès le début.
const levelName = computed(() => levels.value.find((l) => l.id === level.value)?.name ?? '')
const programmes = ref<{ state: 'idle' | 'busy' | 'done'; message: string; failed: boolean }>({
  state: 'idle',
  message: '',
  failed: false,
})

async function downloadProgrammes(): Promise<void> {
  programmes.value = { state: 'busy', message: '', failed: false }
  try {
    const report = await api.downloadProgrammes()
    const got = report.downloaded + report.already
    programmes.value = {
      state: 'done',
      failed: report.errors.length > 0,
      message: report.errors.length
        ? `${got} programme(s) prêt(s), ${report.errors.length} n’ont pas pu être téléchargés : tu pourras réessayer dans « Documents ».`
        : `${got} programme(s) prêt(s).`,
    }
  } catch (e) {
    programmes.value = { state: 'done', failed: true, message: errorMessage(e) }
  }
}

function connectChatGPT(): Promise<void> {
  return run(async () => {
    const { authorization_url } = await api.chatgptLogin()
    window.location.assign(authorization_url)
  })
}

async function finish(destination: string): Promise<void> {
  markSetupDone()
  await router.replace(destination)
}
</script>

<template>
  <section class="card narrow setup">
    <p class="setup-brand"><Sparkles :size="22" aria-hidden="true" /> NoteClaire</p>
    <h1>Bienvenue</h1>
    <p class="hint">Deux minutes pour démarrer · étape {{ step }} sur 3</p>
    <p v-if="error" class="message error" role="alert">{{ error }}</p>

    <form v-if="step === 1" @submit.prevent="saveStudent">
      <h2>Qui va utiliser NoteClaire ?</h2>
      <label for="setup-name">Prénom de l’élève</label>
      <input id="setup-name" v-model="name" type="text" maxlength="100" autocomplete="off" />
      <label for="setup-level">Classe</label>
      <select id="setup-level" v-model="level">
        <option v-for="option in levels" :key="option.id" :value="option.id">
          {{ option.name }}
        </option>
      </select>
      <AdaptationPicker
        id-prefix="setup-adapt"
        :codes="adaptationCodes"
        :free="adaptationNotes"
        @change="onAdaptations"
      />
      <p class="hint">
        L’IA en tient compte pour ses explications. D’autres élèves s’ajoutent plus tard dans les
        Réglages.
      </p>
      <button type="submit" class="primary" :disabled="busy">Continuer</button>
    </form>

    <div v-else-if="step === 2">
      <h2>Quelle IA utiliser ?</h2>
      <AiChoice @saved="onAiSaved">
        <template #before-submit>
          <button type="button" class="secondary" @click="step = 1">Retour</button>
        </template>
      </AiChoice>
    </div>

    <div v-else>
      <h2>C’est prêt</h2>
      <p
        v-if="testResult"
        class="message"
        :class="testResult.ok ? 'success' : 'error'"
        :role="testResult.ok ? 'status' : 'alert'"
      >
        {{ testResult.message }}
      </p>
      <div class="programmes">
        <h3>Programmes officiels · {{ levelName }}</h3>
        <p class="hint">
          L’IA s’en sert pour relire le cours en citant sa source. Ils viennent des sites de
          l’Éducation nationale (Internet nécessaire, une à deux minutes).
        </p>
        <button
          v-if="programmes.state !== 'done' || programmes.failed"
          type="button"
          class="secondary"
          :disabled="programmes.state === 'busy'"
          @click="downloadProgrammes"
        >
          <Download :size="18" aria-hidden="true" />
          {{
            programmes.state === 'busy'
              ? 'Téléchargement…'
              : programmes.failed
                ? 'Réessayer'
                : 'Télécharger les programmes'
          }}
        </button>
        <p
          v-if="programmes.message"
          class="message"
          :class="programmes.failed ? 'warning' : 'success'"
          :role="programmes.failed ? 'alert' : 'status'"
        >
          {{ programmes.message }}
        </p>
        <p v-else class="hint">Tu peux aussi le faire plus tard, dans « Documents ».</p>
      </div>
      <ChatGptHostNotice v-if="provider === 'chatgpt' && !canSignInHere()" />
      <div class="setup-actions">
        <button type="button" class="secondary" @click="step = 2">Modifier l’IA</button>
        <button
          v-if="provider === 'chatgpt' && canSignInHere()"
          type="button"
          class="primary"
          :disabled="busy"
          @click="connectChatGPT"
        >
          Continue with ChatGPT
        </button>
        <button v-else type="button" class="primary" @click="finish('/')">
          {{ provider === 'chatgpt' ? 'Me connecter plus tard' : 'Commencer' }}
        </button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.setup-brand {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0 1rem;
  font-weight: 700;
  color: var(--primary);
}
.programmes {
  margin: 1.25rem 0 0;
  padding-top: 1rem;
  border-top: 1px solid var(--border);
}
.programmes h3 {
  margin: 0 0 0.25rem;
}
.setup-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: space-between;
  margin-top: 1rem;
}
form > .primary {
  margin-top: 1rem;
  width: 100%;
}
</style>
