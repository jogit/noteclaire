<script setup lang="ts">
import { BookMarked, Home, Moon, Settings, Sparkles, Sun, Trash2 } from 'lucide-vue-next'
import { computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useAppearance } from '../composables/useAppearance'
import { subjectStyle, subjectVars } from '../lib/subjects'
import StudentSwitcher from './StudentSwitcher.vue'
import { useSubjects } from '../stores/subjects'

const emit = defineEmits<{ navigate: [] }>()
const { subjects, refresh } = useSubjects()
const { theme } = useAppearance()

const isDark = computed(
  () =>
    theme.value === 'dark' ||
    (theme.value === 'auto' && window.matchMedia?.('(prefers-color-scheme: dark)').matches),
)

function toggleTheme(): void {
  theme.value = isDark.value ? 'light' : 'dark'
}

onMounted(() => {
  refresh().catch(() => {})
})
</script>

<template>
  <nav class="sidebar" aria-label="Navigation principale" @click="emit('navigate')">
    <RouterLink to="/" class="brand">
      <span class="brand-mark"><Sparkles :size="20" aria-hidden="true" /></span>
      NoteClaire
    </RouterLink>

    <StudentSwitcher />

    <ul class="nav-list">
      <li>
        <RouterLink to="/" class="nav-link" exact-active-class="router-link-active">
          <Home :size="20" aria-hidden="true" /> Accueil
        </RouterLink>
      </li>
    </ul>

    <div>
      <p class="nav-section-title">Matières</p>
      <ul class="nav-list">
        <li v-for="subject in subjects" :key="subject.id">
          <RouterLink
            class="nav-link"
            :to="{ name: 'subject', params: { slug: subject.slug } }"
            :style="subjectVars(subject.slug)"
          >
            <span class="subject-dot">
              <component :is="subjectStyle(subject.slug).icon" :size="17" aria-hidden="true" />
            </span>
            {{ subject.name }}
            <span v-if="subject.chapter_count" class="count">
              <span class="visually-hidden">, chapitres : </span>{{ subject.chapter_count }}
            </span>
          </RouterLink>
        </li>
      </ul>
    </div>

    <ul class="nav-list sidebar-footer">
      <li>
        <RouterLink to="/documents" class="nav-link">
          <BookMarked :size="20" aria-hidden="true" /> Documents
        </RouterLink>
      </li>
      <li>
        <RouterLink to="/corbeille" class="nav-link">
          <Trash2 :size="20" aria-hidden="true" /> Corbeille
        </RouterLink>
      </li>
      <li>
        <RouterLink to="/reglages" class="nav-link">
          <Settings :size="20" aria-hidden="true" /> Réglages
        </RouterLink>
      </li>
      <li>
        <button type="button" class="nav-link ghost theme-toggle" @click.stop="toggleTheme">
          <component :is="isDark ? Sun : Moon" :size="20" aria-hidden="true" />
          {{ isDark ? 'Thème clair' : 'Thème sombre' }}
        </button>
      </li>
    </ul>
  </nav>
</template>

<style scoped>
.theme-toggle {
  width: 100%;
  justify-content: flex-start;
  border: none;
}
</style>
