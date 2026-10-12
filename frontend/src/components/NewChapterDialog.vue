<script setup lang="ts">
import { nextTick, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api/client'
import { errorMessage } from '../api/errors'
import { useSubjects } from '../stores/subjects'

const router = useRouter()
const { subjects, refresh, ensureLoaded } = useSubjects()

const dialog = ref<HTMLDialogElement>()
const titleInput = ref<HTMLInputElement>()
const subjectId = ref<number>()
const title = ref('')
const busy = ref(false)
const error = ref('')

async function open(preselectedSubjectId?: number): Promise<void> {
  await ensureLoaded()
  subjectId.value = preselectedSubjectId ?? subjects.value[0]?.id
  title.value = ''
  error.value = ''
  dialog.value?.showModal?.()
  await nextTick()
  titleInput.value?.focus()
}

function close(): void {
  dialog.value?.close?.()
}

async function create(): Promise<void> {
  if (!subjectId.value || !title.value.trim()) return
  busy.value = true
  error.value = ''
  try {
    const chapter = await api.createChapter(subjectId.value, title.value.trim())
    close()
    refresh().catch(() => {})
    await router.push({ name: 'chapter', params: { id: chapter.id } })
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    busy.value = false
  }
}

defineExpose({ open })
</script>

<template>
  <dialog ref="dialog" aria-labelledby="new-chapter-title">
    <form @submit.prevent="create">
      <h2 id="new-chapter-title">Nouveau chapitre</h2>
      <label for="new-chapter-subject">Matière</label>
      <select id="new-chapter-subject" v-model="subjectId" required>
        <option v-for="subject in subjects" :key="subject.id" :value="subject.id">
          {{ subject.name }}
        </option>
      </select>
      <label for="new-chapter-name" class="spaced">Titre du chapitre</label>
      <input
        id="new-chapter-name"
        ref="titleInput"
        v-model="title"
        type="text"
        maxlength="200"
        placeholder="Ex. : Les vecteurs"
        required
      />
      <p v-if="error" class="message error" role="alert">{{ error }}</p>
      <div class="actions">
        <button type="submit" class="primary" :disabled="busy || !title.trim()">Créer</button>
        <button type="button" class="ghost" @click="close">Annuler</button>
      </div>
    </form>
  </dialog>
</template>

<style scoped>
.spaced {
  margin-top: 1rem;
}
</style>
