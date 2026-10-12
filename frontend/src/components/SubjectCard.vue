<script setup lang="ts">
import { RouterLink } from 'vue-router'
import type { Subject } from '../api/types'
import { subjectStyle, subjectVars } from '../lib/subjects'

defineProps<{ subject: Subject }>()
</script>

<template>
  <RouterLink
    class="subject-card"
    :style="subjectVars(subject.slug)"
    :to="{ name: 'subject', params: { slug: subject.slug } }"
  >
    <span class="subject-dot">
      <component :is="subjectStyle(subject.slug).icon" :size="22" aria-hidden="true" />
    </span>
    <div>
      <strong>{{ subject.name }}</strong>
      <span>
        {{
          subject.chapter_count
            ? `${subject.chapter_count} chapitre${subject.chapter_count > 1 ? 's' : ''}`
            : 'Aucun chapitre'
        }}
      </span>
    </div>
  </RouterLink>
</template>
