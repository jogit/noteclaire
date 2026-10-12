<script setup lang="ts">
import { ref } from 'vue'
import MarkdownContent from './MarkdownContent.vue'

// `initial` : texte en cours de modification venu de l'éditeur visuel (sinon le cours enregistré).
const props = defineProps<{ content: string; saving: boolean; initial?: string }>()
const emit = defineEmits<{ save: [content: string]; cancel: []; visual: [draft: string] }>()

const draft = ref(props.initial ?? props.content)
</script>

<template>
  <form class="course-editor" @submit.prevent="emit('save', draft)">
    <p class="hint">
      Écris en Markdown : <code># Titre</code>, <code>- liste</code>, <code>**gras**</code>,
      formules entre <code>$…$</code>.
    </p>
    <div class="editor-columns">
      <div>
        <label for="course-markdown">Cours (Markdown)</label>
        <textarea id="course-markdown" v-model="draft" rows="18" spellcheck="true" />
      </div>
      <div>
        <p class="preview-title" aria-hidden="true">Aperçu</p>
        <MarkdownContent class="preview" :source="draft" />
      </div>
    </div>
    <div class="actions">
      <button
        type="submit"
        class="primary"
        :disabled="saving || !draft.trim() || draft === content"
      >
        Enregistrer
      </button>
      <button type="button" :disabled="saving" @click="emit('cancel')">Annuler</button>
      <button type="button" class="link advanced-link" @click="emit('visual', draft)">
        Revenir à l'éditeur visuel
      </button>
    </div>
  </form>
</template>
