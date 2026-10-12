<script setup lang="ts">
import { Trash2 } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import type { Adaptation, Level, Student, Subject } from '../api/types'
import { loadAdaptations } from '../lib/adaptations'
import AdaptationPicker from './AdaptationPicker.vue'

const props = defineProps<{
  student: Student
  levels: Level[]
  catalog: Subject[]
  canDelete: boolean
}>()
const emit = defineEmits<{
  update: [
    changes: {
      name?: string
      level?: string
      adaptation_codes?: string[]
      adaptation_notes?: string
    },
  ]
  subjects: [ids: number[]]
  remove: []
}>()

const adaptations = ref<Adaptation[]>([])
onMounted(() =>
  loadAdaptations().then(
    (list) => (adaptations.value = list),
    () => {},
  ),
)

const levelName = computed(
  () => props.levels.find((l) => l.id === props.student.level)?.name ?? props.student.level,
)
const followed = computed(() =>
  props.catalog.filter((s) => props.student.subject_ids.includes(s.id)),
)
const usual = computed(() =>
  props.catalog.filter((s) => s.usual_for?.includes(props.student.level)),
)
const others = computed(() =>
  props.catalog.filter((s) => !s.usual_for?.includes(props.student.level)),
)
const particularities = computed(() => [
  ...adaptations.value
    .filter((a) => props.student.adaptation_codes.includes(a.id))
    .map((a) => a.name),
  ...(props.student.adaptation_notes ? [props.student.adaptation_notes] : []),
])

function toggleSubject(id: number, checked: boolean): void {
  const ids = props.student.subject_ids
  emit('subjects', checked ? [...ids, id] : ids.filter((s) => s !== id))
}

function rename(event: Event): void {
  const name = (event.target as HTMLInputElement).value.trim()
  if (name && name !== props.student.name) emit('update', { name })
  else (event.target as HTMLInputElement).value = props.student.name
}
</script>

<template>
  <article class="card student-card" :aria-label="`Élève ${student.name}`">
    <header class="student-head">
      <span class="avatar" aria-hidden="true">{{ student.name.charAt(0).toUpperCase() }}</span>
      <div class="identity">
        <label :for="`student-name-${student.id}`" class="visually-hidden">Prénom</label>
        <input
          :id="`student-name-${student.id}`"
          class="name-input"
          type="text"
          maxlength="100"
          :value="student.name"
          @change="rename"
        />
        <label :for="`student-level-${student.id}`" class="visually-hidden">Classe</label>
        <select
          :id="`student-level-${student.id}`"
          class="level-select"
          :value="student.level"
          @change="emit('update', { level: ($event.target as HTMLSelectElement).value })"
        >
          <option v-for="level in levels" :key="level.id" :value="level.id">
            {{ level.name }}
          </option>
        </select>
      </div>
      <button
        v-if="canDelete"
        type="button"
        class="ghost icon"
        :aria-label="`Supprimer ${student.name}`"
        @click="emit('remove')"
      >
        <Trash2 :size="20" aria-hidden="true" />
      </button>
    </header>

    <section class="block" :aria-label="`Matières de ${student.name}`">
      <h3>Matières</h3>
      <p v-if="!followed.length" class="hint">Aucune matière choisie.</p>
      <ul v-else class="chips">
        <li v-for="subject in followed" :key="subject.id" class="chip info">{{ subject.name }}</li>
      </ul>
      <details class="edit">
        <summary>Modifier les matières</summary>
        <fieldset class="picks">
          <legend>Habituelles en {{ levelName.toLowerCase() }}</legend>
          <label v-for="subject in usual" :key="subject.id" class="pick">
            <input
              type="checkbox"
              :checked="student.subject_ids.includes(subject.id)"
              @change="toggleSubject(subject.id, ($event.target as HTMLInputElement).checked)"
            />
            {{ subject.name }}
          </label>
        </fieldset>
        <details v-if="others.length" class="more">
          <summary>Autres matières, options et séries</summary>
          <fieldset class="picks">
            <legend class="visually-hidden">Autres matières</legend>
            <label v-for="subject in others" :key="subject.id" class="pick">
              <input
                type="checkbox"
                :checked="student.subject_ids.includes(subject.id)"
                @change="toggleSubject(subject.id, ($event.target as HTMLInputElement).checked)"
              />
              {{ subject.name }}
            </label>
          </fieldset>
        </details>
      </details>
    </section>

    <section class="block" :aria-label="`Particularités de ${student.name}`">
      <h3>Particularités</h3>
      <p v-if="!particularities.length" class="hint">
        Aucune. L’IA s’en sert pour adapter ses explications.
      </p>
      <ul v-else class="chips">
        <li v-for="item in particularities" :key="item" class="chip">{{ item }}</li>
      </ul>
      <details class="edit">
        <summary>Modifier les particularités</summary>
        <AdaptationPicker
          :id-prefix="`student-adapt-${student.id}`"
          :codes="student.adaptation_codes"
          :free="student.adaptation_notes"
          @change="
            emit('update', { adaptation_codes: $event.codes, adaptation_notes: $event.free })
          "
        />
      </details>
    </section>
  </article>
</template>

<style scoped>
.student-head {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.25rem;
}
.avatar {
  display: grid;
  place-items: center;
  flex: none;
  width: 3rem;
  height: 3rem;
  border-radius: 999px;
  background: var(--primary-soft);
  color: var(--primary);
  font-weight: 700;
  font-size: 1.25rem;
}
.identity {
  flex: 1;
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 0.75rem;
  align-items: center;
}
.name-input {
  flex: 1 1 10rem;
  min-width: 0;
  font-weight: 600;
  font-size: 1.1rem;
}
.level-select {
  flex: 0 1 14rem;
}
.block {
  padding-top: 1rem;
  border-top: 1px solid var(--border);
}
.block + .block {
  margin-top: 1rem;
}
.block h3 {
  margin: 0 0 0.5rem;
  font-size: 0.95rem;
  color: var(--muted);
  font-weight: 600;
}
.edit {
  margin-top: 0.75rem;
}
.edit > summary,
.more > summary {
  cursor: pointer;
  color: var(--primary);
  font-weight: 600;
  padding: 0.25rem 0;
}
.picks {
  border: 0;
  padding: 0;
  margin: 0.75rem 0;
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1.25rem;
}
.picks legend {
  font-weight: 600;
  padding: 0;
  margin-bottom: 0.5rem;
}
.pick {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  cursor: pointer;
}
.chips {
  list-style: none;
  margin: 0;
  padding: 0;
}
.hint {
  margin: 0;
}
</style>
