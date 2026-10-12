<script setup lang="ts">
import { Printer } from 'lucide-vue-next'
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api/client'
import { errorMessage } from '../api/errors'
import type { Chapter } from '../api/types'
import MarkdownContent from '../components/MarkdownContent.vue'
import { subjectStyle, subjectVars } from '../lib/subjects'

/**
 * Vue d'impression (SPEC §24) : le PDF est produit par « Imprimer → Enregistrer en PDF »
 * du navigateur, ce qui garde le rendu exact des formules et des schémas.
 */
const props = defineProps<{ id: string }>()
const route = useRoute()

const chapter = ref<Chapter>()
const content = ref('')
const version = ref<number>()
const error = ref('')
const markdown = ref<InstanceType<typeof MarkdownContent>>()

const isSheet = computed(() => route.query.quoi === 'fiche')
const style = computed(() => subjectStyle(chapter.value?.subject.slug))
const today = new Intl.DateTimeFormat('fr-FR', { dateStyle: 'long' }).format(new Date())
const meta = computed(() =>
  [
    isSheet.value ? 'Fiche de révision' : 'Cours',
    version.value ? `version ${version.value}` : '',
    today,
  ]
    .filter(Boolean)
    .join(' · '),
)

onMounted(async () => {
  const id = Number(props.id)
  try {
    chapter.value = await api.chapter(id)
    if (isSheet.value) {
      const sheet = await api.revisionSheet(id)
      content.value = sheet?.content_markdown ?? ''
      version.value = sheet?.course_version
    } else {
      const course = await api.course(id)
      content.value = course?.content_markdown ?? ''
      version.value = course?.version
    }
    if (!content.value) {
      error.value = isSheet.value ? 'Aucune fiche de révision.' : 'Aucun cours mis au propre.'
      return
    }
    document.title = `${chapter.value.title} — ${chapter.value.subject.name}`
    await nextTick()
    // Les schémas et les polices doivent être prêts avant d'ouvrir l'impression.
    await markdown.value?.ready()
    await document.fonts?.ready
    if (route.query.auto !== '0') window.print()
  } catch (e) {
    error.value = errorMessage(e)
  }
})

function print(): void {
  window.print()
}
</script>

<template>
  <div class="print-page" :style="chapter ? subjectVars(chapter.subject.slug) : undefined">
    <p v-if="error" class="message error" role="alert">{{ error }}</p>
    <div class="print-toolbar no-print">
      <button type="button" class="primary" @click="print">
        <Printer :size="20" aria-hidden="true" /> Imprimer / Enregistrer en PDF
      </button>
      <p class="hint">Dans la fenêtre d'impression, choisis « Enregistrer au format PDF ».</p>
    </div>
    <article v-if="chapter && content" class="print-sheet" :class="{ 'is-sheet': isSheet }">
      <header class="print-header">
        <span class="print-subject">
          <component :is="style.icon" :size="18" aria-hidden="true" />
          {{ chapter.subject.name }}
        </span>
        <h1 class="print-title">{{ chapter.title }}</h1>
        <p class="print-meta">{{ meta }}</p>
      </header>
      <MarkdownContent ref="markdown" class="print-content" :source="content" />
    </article>
  </div>
</template>
