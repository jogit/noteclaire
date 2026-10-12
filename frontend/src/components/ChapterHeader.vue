<script setup lang="ts">
import { Check, Download, MoreHorizontal, Pencil, Printer, Trash2 } from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '../api/client'
import { errorMessage } from '../api/errors'
import type { Chapter } from '../api/types'
import { subjectStyle, subjectVars } from '../lib/subjects'

const props = defineProps<{ chapter: Chapter; hasCourse: boolean }>()
const emit = defineEmits<{ renamed: [chapter: Chapter]; deleted: []; error: [message: string] }>()

const menuOpen = ref(false)
const renaming = ref(false)
const newTitle = ref('')
const style = computed(() => subjectStyle(props.chapter.subject.slug))

function startRename(): void {
  menuOpen.value = false
  newTitle.value = props.chapter.title
  renaming.value = true
}

async function rename(): Promise<void> {
  const title = newTitle.value.trim()
  if (!title) return
  try {
    emit('renamed', await api.renameChapter(props.chapter.id, title))
    renaming.value = false
  } catch (e) {
    emit('error', errorMessage(e))
  }
}

async function deleteChapter(): Promise<void> {
  menuOpen.value = false
  const confirmed = window.confirm(
    `Mettre le chapitre « ${props.chapter.title} » à la corbeille ? Tu pourras le récupérer ` +
      'pendant 30 jours depuis la Corbeille.',
  )
  if (!confirmed) return
  try {
    await api.deleteChapter(props.chapter.id)
    emit('deleted')
  } catch (e) {
    emit('error', errorMessage(e))
  }
}

function closeMenu(event: MouseEvent): void {
  if (!(event.target as HTMLElement).closest('.menu')) menuOpen.value = false
}

onMounted(() => document.addEventListener('click', closeMenu))
onBeforeUnmount(() => document.removeEventListener('click', closeMenu))
</script>

<template>
  <header class="chapter-header" :style="subjectVars(chapter.subject.slug)">
    <div class="grow">
      <RouterLink
        class="subject-chip"
        :to="{ name: 'subject', params: { slug: chapter.subject.slug } }"
      >
        <span class="subject-dot"
          ><component :is="style.icon" :size="15" aria-hidden="true"
        /></span>
        {{ chapter.subject.name }}
      </RouterLink>
      <form v-if="renaming" class="rename-form" @submit.prevent="rename">
        <label for="rename" class="visually-hidden">Nouveau titre</label>
        <input id="rename" v-model="newTitle" type="text" maxlength="200" required />
        <button type="submit" class="primary"><Check :size="18" aria-hidden="true" /> OK</button>
        <button type="button" class="ghost" @click="renaming = false">Annuler</button>
      </form>
      <h1 v-else>{{ chapter.title }}</h1>
    </div>

    <div class="menu">
      <button
        type="button"
        class="icon ghost"
        aria-label="Plus d'actions"
        :aria-expanded="menuOpen"
        @click="menuOpen = !menuOpen"
      >
        <MoreHorizontal :size="22" aria-hidden="true" />
      </button>
      <div v-if="menuOpen" class="menu-panel">
        <button type="button" @click="startRename">
          <Pencil :size="18" aria-hidden="true" /> Renommer
        </button>
        <RouterLink
          v-if="hasCourse"
          class="button-link"
          :to="{ name: 'print', params: { id: chapter.id } }"
          target="_blank"
          @click="menuOpen = false"
        >
          <Printer :size="18" aria-hidden="true" /> Exporter le cours en PDF
        </RouterLink>
        <a
          v-if="hasCourse"
          class="button-link"
          :href="api.exportMarkdownUrl(chapter.id)"
          download
          @click="menuOpen = false"
        >
          <Download :size="18" aria-hidden="true" /> Télécharger en Markdown
        </a>
        <button type="button" class="danger-item" @click="deleteChapter">
          <Trash2 :size="18" aria-hidden="true" /> Supprimer ce chapitre
        </button>
      </div>
    </div>
  </header>
</template>
