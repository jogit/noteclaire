<script setup lang="ts">
import { onMounted, ref } from 'vue'
import type { Adaptation } from '../api/types'
import { loadAdaptations } from '../lib/adaptations'

const props = defineProps<{ idPrefix: string; codes: string[]; free: string }>()
const emit = defineEmits<{ change: [value: { codes: string[]; free: string }] }>()

const options = ref<Adaptation[]>([])
const free = ref(props.free)

onMounted(async () => {
  try {
    options.value = await loadAdaptations()
  } catch {
    // la liste reste vide : le champ libre fonctionne quand même
  }
})

function toggle(id: string, checked: boolean): void {
  const codes = checked ? [...props.codes, id] : props.codes.filter((c) => c !== id)
  emit('change', { codes, free: free.value })
}

function saveFree(): void {
  emit('change', { codes: props.codes, free: free.value })
}
</script>

<template>
  <fieldset class="adaptations">
    <legend>Particularités (facultatif)</legend>
    <div class="adaptation-options">
      <label v-for="option in options" :key="option.id" class="adaptation-option">
        <input
          type="checkbox"
          :checked="codes.includes(option.id)"
          @change="toggle(option.id, ($event.target as HTMLInputElement).checked)"
        />
        {{ option.name }}
      </label>
    </div>
    <label :for="`${idPrefix}-free`">Autre précision</label>
    <input
      :id="`${idPrefix}-free`"
      v-model="free"
      type="text"
      maxlength="300"
      placeholder="Ex. : se concentre mieux avec des exemples concrets"
      @change="saveFree"
    />
  </fieldset>
</template>

<style scoped>
.adaptations {
  border: 0;
  padding: 0;
  margin: 0;
  grid-column: 1 / -1;
}
legend {
  font-weight: 600;
  padding: 0;
  margin-bottom: 0.5rem;
}
.adaptation-options {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1.25rem;
  margin-bottom: 0.75rem;
}
.adaptation-option {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  cursor: pointer;
}
</style>
