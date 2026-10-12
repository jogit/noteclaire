<script setup lang="ts">
import { Plus } from 'lucide-vue-next'
import { onMounted, ref, watch } from 'vue'
import { api } from '../api/client'
import { errorMessage } from '../api/errors'
import type { Level, Subject } from '../api/types'
import { useStudents } from '../stores/students'
import { useSubjects } from '../stores/subjects'
import StudentCard from './StudentCard.vue'

const props = defineProps<{ catalogVersion?: number }>()

const { students, current, refresh } = useStudents()
const { refresh: refreshMenu } = useSubjects()
const levels = ref<Level[]>([])
const catalog = ref<Subject[]>([])
const newName = ref('')
const newLevel = ref('seconde')
const error = ref('')

async function run(action: () => Promise<unknown>): Promise<void> {
  error.value = ''
  try {
    await action()
  } catch (e) {
    error.value = errorMessage(e)
  }
  await refresh().catch(() => {})
  await refreshMenu().catch(() => {}) // la classe et les matières changent le menu
}

async function loadCatalog(): Promise<void> {
  catalog.value = await api.subjects(true)
}

function update(id: number, changes: Parameters<typeof api.updateStudent>[1]): Promise<void> {
  return run(() => api.updateStudent(id, changes))
}

function setSubjects(id: number, subjectIds: number[]): Promise<void> {
  return run(() => api.setStudentSubjects(id, subjectIds))
}

function remove(id: number, name: string): Promise<void> {
  if (!window.confirm(`Supprimer l’élève « ${name} » ?`)) return Promise.resolve()
  return run(() => api.deleteStudent(id))
}

async function add(): Promise<void> {
  const name = newName.value.trim()
  if (!name) return
  await run(() => api.createStudent(name, newLevel.value))
  if (!error.value) newName.value = ''
}

watch(
  () => props.catalogVersion,
  () => loadCatalog().catch(() => {}),
)

onMounted(async () => {
  try {
    ;[levels.value] = await Promise.all([api.levels(), loadCatalog(), refresh()])
  } catch (e) {
    error.value = errorMessage(e)
  }
})
</script>

<template>
  <p class="intro">
    Chaque enfant a son espace : ses chapitres, ses matières et sa classe. La classe règle le niveau
    des explications de l’IA et les programmes officiels utilisés.
  </p>
  <p v-if="error" class="message error" role="alert">{{ error }}</p>

  <StudentCard
    v-for="student in students"
    :key="student.id"
    :student="student"
    :levels="levels"
    :catalog="catalog"
    :can-delete="students.length > 1 && student.id !== current?.id"
    @update="update(student.id, $event)"
    @subjects="setSubjects(student.id, $event)"
    @remove="remove(student.id, student.name)"
  />

  <details class="card add-student">
    <summary><Plus :size="18" aria-hidden="true" /> Ajouter un élève</summary>
    <form class="form-grid" @submit.prevent="add">
      <div>
        <label for="new-student-name">Prénom</label>
        <input id="new-student-name" v-model="newName" type="text" maxlength="100" required />
      </div>
      <div>
        <label for="new-student-level">Classe</label>
        <select id="new-student-level" v-model="newLevel">
          <option v-for="level in levels" :key="level.id" :value="level.id">
            {{ level.name }}
          </option>
        </select>
      </div>
      <button type="submit" class="primary">Ajouter l’élève</button>
    </form>
  </details>
</template>

<style scoped>
.intro {
  margin-top: 0;
  color: var(--muted);
}
.add-student > summary {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  font-weight: 600;
  color: var(--primary);
}
.add-student form {
  margin-top: 1rem;
  align-items: end;
}
</style>
