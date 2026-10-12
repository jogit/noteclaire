<script setup lang="ts">
import { Plus, Trash2 } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import { api } from '../api/client'
import { errorMessage } from '../api/errors'
import type { Subject } from '../api/types'
import { useSubjects } from '../stores/subjects'

const { refresh: refreshMenu } = useSubjects()
const emit = defineEmits<{ changed: [] }>()
const subjects = ref<Subject[]>([])
const newName = ref('')
const error = ref('')

async function load(): Promise<void> {
  subjects.value = await api.subjects(true)
}

async function run(action: () => Promise<unknown>): Promise<void> {
  error.value = ''
  try {
    await action()
    await load()
    await refreshMenu()
    emit('changed')
  } catch (e) {
    error.value = errorMessage(e)
    await load().catch(() => {})
  }
}

function add(): Promise<void> {
  const name = newName.value.trim()
  if (!name) return Promise.resolve()
  return run(async () => {
    await api.createSubject(name)
    newName.value = ''
  })
}

function rename(subject: Subject, event: Event): Promise<void> {
  const name = (event.target as HTMLInputElement).value.trim()
  if (!name || name === subject.name) return load()
  return run(() => api.updateSubject(subject.id, { name }))
}

function remove(subject: Subject): Promise<void> {
  if (!window.confirm(`Supprimer la matière « ${subject.name} » ?`)) return Promise.resolve()
  return run(() => api.deleteSubject(subject.id))
}

onMounted(() => run(() => Promise.resolve()))
</script>

<template>
  <section class="card" aria-labelledby="subjects-title">
    <h2 id="subjects-title">Catalogue des matières</h2>
    <p class="hint">
      Ce catalogue est commun à tous les élèves ; chaque élève coche ses matières dans sa fiche
      (onglet « Élèves »). Renommer ou supprimer une matière vaut pour tous, et on ne peut supprimer
      qu’une matière sans chapitre ni document.
    </p>
    <p v-if="error" class="message error" role="alert">{{ error }}</p>

    <ul class="subjects">
      <li v-for="subject in subjects" :key="subject.id">
        <label :for="`subject-name-${subject.id}`" class="visually-hidden">
          Nom de la matière {{ subject.name }}
        </label>
        <input
          :id="`subject-name-${subject.id}`"
          type="text"
          maxlength="100"
          :value="subject.name"
          @change="rename(subject, $event)"
        />
        <span class="slug" title="Nom du dossier des documents de référence">{{
          subject.slug
        }}</span>
        <button
          type="button"
          class="ghost icon"
          :aria-label="`Supprimer ${subject.name}`"
          @click="remove(subject)"
        >
          <Trash2 :size="18" aria-hidden="true" />
        </button>
      </li>
    </ul>

    <form class="add" @submit.prevent="add">
      <div>
        <label for="new-subject-name">Nouvelle matière</label>
        <input id="new-subject-name" v-model="newName" type="text" maxlength="100" required />
      </div>
      <button type="submit" class="secondary">
        <Plus :size="18" aria-hidden="true" /> Ajouter
      </button>
    </form>
  </section>
</template>

<style scoped>
.add {
  display: flex;
  align-items: end;
  gap: 0.75rem;
}
.add > div {
  flex: 1;
}
.add input {
  margin: 0;
}

.subjects {
  list-style: none;
  margin: 1rem 0;
  padding: 0;
  display: grid;
  gap: 0.35rem;
}
.subjects li {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.subjects input {
  flex: 1;
  min-width: 0;
}
.slug {
  flex: 0 1 12rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.95rem;
  color: var(--muted);
}
@media (max-width: 640px) {
  .slug {
    display: none;
  }
}
</style>
