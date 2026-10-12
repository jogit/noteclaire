<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AiChoice from '../components/AiChoice.vue'
import AppVersion from '../components/AppVersion.vue'
import BackupSection from '../components/BackupSection.vue'
import ChatGptSection from '../components/ChatGptSection.vue'
import StudentsSection from '../components/StudentsSection.vue'
import SubjectsSection from '../components/SubjectsSection.vue'
import UsageSection from '../components/UsageSection.vue'
import { SPACINGS, TEXT_SIZES, THEMES, useAppearance } from '../composables/useAppearance'

const TABS = [
  { id: 'eleves', label: 'Élèves' },
  { id: 'ia', label: 'Intelligence artificielle' },
  { id: 'sauvegardes', label: 'Sauvegardes' },
  { id: 'affichage', label: 'Affichage' },
  { id: 'avance', label: 'Avancé' },
]

const route = useRoute()
const router = useRouter()
const { size: textSize, theme, spacing } = useAppearance()

// L'onglet est dans l'adresse (?onglet=ia) : on le retrouve au rechargement ; le retour de la
// connexion ChatGPT (?chatgpt=…) ouvre l'onglet de l'IA.
const requested = route.query.chatgpt ? 'ia' : String(route.query.onglet ?? '')
const tab = ref(TABS.some((t) => t.id === requested) ? requested : 'eleves')
const catalogVersion = ref(0)
const aiVersion = ref(0)
const aiResult = ref<{ ok: boolean; message: string }>()

function select(id: string): void {
  tab.value = id
  router.replace({ query: { onglet: id } })
}

function onAiSaved(result: { ok: boolean; message: string }): void {
  aiResult.value = result
  aiVersion.value++
}
</script>

<template>
  <header class="page-header">
    <h1>Réglages</h1>
  </header>

  <div class="tabs scroll" role="tablist" aria-label="Rubriques des réglages">
    <button
      v-for="item in TABS"
      :id="`tab-${item.id}`"
      :key="item.id"
      type="button"
      role="tab"
      class="tab"
      :aria-selected="tab === item.id"
      :aria-controls="`panel-${item.id}`"
      @click="select(item.id)"
    >
      {{ item.label }}
    </button>
  </div>

  <div :id="`panel-${tab}`" role="tabpanel" :aria-labelledby="`tab-${tab}`">
    <template v-if="tab === 'eleves'">
      <StudentsSection :catalog-version="catalogVersion" />
    </template>

    <template v-else-if="tab === 'ia'">
      <section class="card" aria-labelledby="ai-title">
        <h2 id="ai-title">IA utilisée</h2>
        <p
          v-if="aiResult"
          class="message"
          :class="aiResult.ok ? 'success' : 'error'"
          :role="aiResult.ok ? 'status' : 'alert'"
        >
          {{ aiResult.message }}
        </p>
        <AiChoice submit-label="Enregistrer et tester" @saved="onAiSaved" />
      </section>
      <ChatGptSection :key="aiVersion" />
      <UsageSection />
    </template>

    <BackupSection v-else-if="tab === 'sauvegardes'" />

    <section v-else-if="tab === 'affichage'" class="card" aria-labelledby="appearance-title">
      <h2 id="appearance-title">Affichage</h2>
      <p class="hint">
        Réglages de confort de lecture, mémorisés sur cet appareil. Le thème « Crème » et
        l’espacement « Aéré » aident beaucoup de lecteurs dys.
      </p>
      <div class="form-grid">
        <div>
          <label for="theme">Thème</label>
          <select id="theme" v-model="theme">
            <option v-for="(label, key) in THEMES" :key="key" :value="key">{{ label }}</option>
          </select>
        </div>
        <div>
          <label for="spacing">Espacement du texte</label>
          <select id="spacing" v-model="spacing">
            <option v-for="(label, key) in SPACINGS" :key="key" :value="key">{{ label }}</option>
          </select>
        </div>
        <div>
          <label for="text-size">Taille du texte</label>
          <select id="text-size" v-model="textSize">
            <option v-for="(option, key) in TEXT_SIZES" :key="key" :value="key">
              {{ option.label }}
            </option>
          </select>
        </div>
      </div>
    </section>

    <template v-else-if="tab === 'avance'">
      <SubjectsSection @changed="catalogVersion++" />
      <AppVersion />
    </template>
  </div>
</template>
