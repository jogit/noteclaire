<script setup lang="ts">
import { Download, FileText, Trash2 } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { api } from '../api/client'
import { errorMessage } from '../api/errors'
import type { Level, ReferenceDocument, Subject } from '../api/types'
import { useStudents } from '../stores/students'

const { current, refresh: refreshStudents } = useStudents()
const levels = ref<Level[]>([])
const subjects = ref<Subject[]>([])
const documents = ref<ReferenceDocument[]>([])
const error = ref('')
const message = ref('')
const failures = ref<string[]>([])
const busy = ref(false)

const form = ref({ subjectId: 0, title: '', source: '', url: '' })
const file = ref<File | null>(null)
const fileInput = ref<HTMLInputElement>()

const levelName = computed(
  () => levels.value.find((l) => l.id === current.value?.level)?.name ?? 'sa classe',
)
const groups = computed(() =>
  subjects.value
    .map((subject) => ({
      subject,
      documents: documents.value.filter((d) => d.subject_id === subject.id),
    }))
    .filter((group) => group.documents.length),
)

async function load(): Promise<void> {
  try {
    ;[subjects.value, documents.value] = await Promise.all([api.subjects(true), api.references()])
    if (!form.value.subjectId && subjects.value[0]) form.value.subjectId = subjects.value[0].id
  } catch (e) {
    error.value = errorMessage(e)
  }
}

onMounted(async () => {
  try {
    ;[levels.value] = await Promise.all([api.levels(), refreshStudents(), load()])
  } catch (e) {
    error.value = errorMessage(e)
  }
})

/** Lance une action longue : un seul message à la fois, bouton bloqué pendant l'attente. */
async function run(action: () => Promise<string>): Promise<void> {
  busy.value = true
  error.value = ''
  message.value = ''
  failures.value = []
  try {
    message.value = await action()
    await load()
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    busy.value = false
  }
}

function downloadProgrammes(): Promise<void> {
  return run(async () => {
    const report = await api.downloadProgrammes()
    failures.value = report.errors
    return report.downloaded
      ? `${report.downloaded} programme(s) téléchargé(s).`
      : 'Tous les programmes officiels sont déjà présents.'
  })
}

function sync(): Promise<void> {
  return run(async () => {
    const report = await api.syncReferences()
    failures.value = report.errors
    return `Dossier relu : ${report.added} ajouté(s), ${report.updated} mis à jour, ${report.removed} retiré(s).`
  })
}

function upload(): Promise<void> {
  return run(async () => {
    if (!file.value) return ''
    const { subjectId, ...metadata } = form.value
    const document = await api.uploadReference(subjectId, file.value, metadata)
    form.value = { subjectId, title: '', source: '', url: '' }
    file.value = null
    if (fileInput.value) fileInput.value.value = ''
    return `« ${document.title} » a été ajouté.`
  })
}

function onFile(event: Event): void {
  file.value = (event.target as HTMLInputElement).files?.[0] ?? null
}

async function remove(document: ReferenceDocument): Promise<void> {
  if (!window.confirm(`Supprimer « ${document.title} » ?`)) return
  error.value = ''
  try {
    await api.deleteReference(document.id)
    await load()
  } catch (e) {
    error.value = errorMessage(e)
  }
}
</script>

<template>
  <header class="page-header">
    <h1>Programmes et documents</h1>
    <p>
      L’IA s’appuie sur ces documents pour relire les cours de
      <strong>{{ current?.name ?? 'l’élève' }}</strong> ({{ levelName }}) et citer sa source.
    </p>
  </header>

  <section class="card official" aria-labelledby="official-title">
    <div>
      <h2 id="official-title">Programmes officiels · {{ levelName }}</h2>
      <p class="hint">
        Récupérés sur les sites officiels de l’Éducation nationale (Internet nécessaire). Seuls les
        manquants sont téléchargés.
      </p>
    </div>
    <button type="button" class="primary" :disabled="busy" @click="downloadProgrammes">
      <Download :size="18" aria-hidden="true" />
      {{ busy ? 'Un instant…' : 'Télécharger les programmes officiels' }}
    </button>
  </section>

  <p v-if="message" class="message success" role="status">{{ message }}</p>
  <p v-if="error" class="message error" role="alert">{{ error }}</p>
  <ul v-if="failures.length" class="message warning" role="alert">
    <li v-for="failure in failures" :key="failure">{{ failure }}</li>
  </ul>

  <section v-if="!groups.length" class="card empty">
    <FileText :size="32" aria-hidden="true" />
    <p>
      Aucun document pour l’instant. Cliquez sur « Télécharger les programmes officiels » pour
      récupérer ceux de {{ levelName.toLowerCase() }}.
    </p>
  </section>

  <section v-if="groups.length" class="card" aria-label="Documents">
    <div v-for="group in groups" :key="group.subject.id" class="group">
      <h2>{{ group.subject.name }}</h2>
      <ul class="docs">
        <li v-for="document in group.documents" :key="document.id">
          <div class="doc-text">
            <a
              v-if="document.url"
              :href="document.url"
              target="_blank"
              rel="noopener"
              class="doc-title"
              title="Ouvrir l’original dans un nouvel onglet"
              >{{ document.title }}</a
            >
            <strong v-else class="doc-title">{{ document.title }}</strong>
            <span v-if="document.source" class="hint doc-source" :title="document.source">
              {{ document.source }}
            </span>
          </div>
          <button
            type="button"
            class="ghost icon"
            :aria-label="`Supprimer ${document.title}`"
            @click="remove(document)"
          >
            <Trash2 :size="18" aria-hidden="true" />
          </button>
        </li>
      </ul>
    </div>
  </section>

  <details class="card advanced">
    <summary>Ajouter un document personnel ou relire le dossier</summary>
    <form class="advanced-form" @submit.prevent="upload">
      <p class="hint">
        PDF, Markdown ou texte : un manuel, une fiche de l’enseignant… Vous pouvez aussi déposer les
        fichiers dans <code>data/references/&lt;classe&gt;/&lt;matière&gt;/</code>, puis relire le
        dossier.
      </p>
      <div class="form-grid">
        <div>
          <label for="ref-subject">Matière</label>
          <select id="ref-subject" v-model="form.subjectId" required>
            <option v-for="subject in subjects" :key="subject.id" :value="subject.id">
              {{ subject.name }}
            </option>
          </select>
        </div>
        <div>
          <label for="ref-file">Fichier</label>
          <input
            id="ref-file"
            ref="fileInput"
            type="file"
            accept=".pdf,.md,.txt"
            @change="onFile"
          />
        </div>
        <div>
          <label for="ref-title">Titre (facultatif)</label>
          <input id="ref-title" v-model="form.title" type="text" />
        </div>
        <div>
          <label for="ref-source">Source (facultatif)</label>
          <input id="ref-source" v-model="form.source" type="text" />
        </div>
      </div>
      <div class="actions">
        <button type="submit" class="primary" :disabled="busy || !file">Ajouter</button>
        <button type="button" class="secondary" :disabled="busy" @click="sync">
          Relire le dossier
        </button>
      </div>
    </form>
  </details>
</template>

<style scoped>
.official {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  background: var(--primary-soft);
  border-color: transparent;
}
.official h2 {
  margin: 0 0 0.25rem;
}
.official .hint {
  margin: 0;
}
.empty {
  display: grid;
  justify-items: center;
  gap: 0.5rem;
  text-align: center;
  color: var(--muted);
}
.empty p {
  margin: 0;
}
.group + .group {
  margin-top: 1.5rem;
}
.group h2 {
  margin: 0 0 0.25rem;
  font-size: 1rem;
  color: var(--muted);
  letter-spacing: 0.04em;
}
.docs {
  list-style: none;
  margin: 0;
  padding: 0;
}
.docs li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.55rem 0;
  border-top: 1px solid var(--border);
}
.doc-text {
  display: grid;
  min-width: 0;
}
.doc-title {
  font-weight: 600;
  color: var(--text);
  text-decoration: none;
}
a.doc-title:hover {
  color: var(--primary);
  text-decoration: underline;
}
.doc-source {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.95rem;
}
.advanced > summary {
  cursor: pointer;
  font-weight: 600;
  color: var(--primary);
}
.advanced-form {
  margin-top: 1rem;
}
</style>
