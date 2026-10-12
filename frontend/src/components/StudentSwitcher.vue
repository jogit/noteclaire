<script setup lang="ts">
import { onMounted } from 'vue'
import { useStudents } from '../stores/students'

const { students, current, refresh, switchTo } = useStudents()

onMounted(() => {
  refresh().catch(() => {})
})

function onChange(event: Event): void {
  switchTo(Number((event.target as HTMLSelectElement).value))
}
</script>

<template>
  <div v-if="students.length > 1 && current" class="student-switcher">
    <label for="student-select" class="nav-section-title">Élève</label>
    <select id="student-select" :value="current.id" @change="onChange">
      <option v-for="student in students" :key="student.id" :value="student.id">
        {{ student.name }}
      </option>
    </select>
  </div>
</template>

<style scoped>
.student-switcher {
  display: grid;
  gap: 0.25rem;
}
</style>
