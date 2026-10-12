<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { renderDiagrams } from '../lib/diagrams'
import { renderMarkdown } from '../lib/markdown'

const props = defineProps<{ source: string; canAddImages?: boolean }>()
const emit = defineEmits<{ 'add-schema-image': [index: number] }>()

const root = ref<HTMLElement>()
// Sûr : markdown-it est configuré avec html: false ; seules nos balises sont produites.
const html = computed(() => renderMarkdown(props.source))

let drawing: Promise<void> = Promise.resolve()

function drawDiagrams(): Promise<void> {
  drawing = nextTick().then(() =>
    root.value ? renderDiagrams(root.value).catch(() => {}) : undefined,
  )
  return drawing
}

// Pour l'impression : attendre que les schémas soient dessinés.
defineExpose({ ready: () => drawing })

function onClick(event: MouseEvent): void {
  const button = (event.target as HTMLElement).closest<HTMLElement>(
    '[data-action="add-schema-image"]',
  )
  if (button) emit('add-schema-image', Number(button.dataset.schemaIndex))
}

onMounted(drawDiagrams)
watch(html, drawDiagrams)
</script>

<template>
  <!-- eslint-disable vue/no-v-html -- HTML produit par markdown-it (html: false) -->
  <div
    ref="root"
    class="markdown"
    :class="{ 'can-add-images': canAddImages }"
    @click="onClick"
    v-html="html"
  />
</template>
