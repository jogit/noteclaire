<script setup lang="ts">
import { Menu, Search } from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, provide, ref } from 'vue'
import { RouterView, useRoute, useRouter } from 'vue-router'
import NewChapterDialog from './components/NewChapterDialog.vue'
import SideNav from './components/SideNav.vue'
import { useAppearance } from './composables/useAppearance'

useAppearance() // applique le thème et la taille du texte dès le démarrage

const route = useRoute()
const router = useRouter()
const query = ref('')
const navOpen = ref(false)
const searchInput = ref<HTMLInputElement>()
const newChapter = ref<InstanceType<typeof NewChapterDialog>>()

// Connexion et impression s'affichent sans menu.
const bare = computed(() => route.meta.bare === true)

provide('openNewChapter', (subjectId?: number) => newChapter.value?.open(subjectId))

function search(): void {
  if (query.value.trim()) router.push({ name: 'search', query: { q: query.value.trim() } })
}

function onKeydown(event: KeyboardEvent): void {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault()
    searchInput.value?.focus()
  }
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <RouterView v-if="bare" />
  <div v-else class="shell" :class="{ 'nav-open': navOpen }">
    <SideNav @navigate="navOpen = false" />
    <div class="scrim" aria-hidden="true" @click="navOpen = false" />
    <div class="main-col">
      <header class="topbar no-print">
        <button
          type="button"
          class="menu-button icon ghost"
          :aria-expanded="navOpen"
          aria-label="Ouvrir le menu"
          @click="navOpen = !navOpen"
        >
          <Menu :size="22" aria-hidden="true" />
        </button>
        <form class="header-search" role="search" @submit.prevent="search">
          <Search :size="18" aria-hidden="true" />
          <label for="search" class="visually-hidden">Rechercher dans mes cours</label>
          <input
            id="search"
            ref="searchInput"
            v-model="query"
            type="search"
            placeholder="Rechercher dans mes cours"
            title="Raccourci : Ctrl+K"
          />
          <button type="submit" class="visually-hidden">Rechercher</button>
        </form>
      </header>
      <main class="content">
        <RouterView />
      </main>
    </div>
    <NewChapterDialog ref="newChapter" />
  </div>
</template>
