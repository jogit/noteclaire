<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../api/client'
import type { Usage } from '../api/types'

const usage = ref<Usage>()

const euros = new Intl.NumberFormat('fr-FR', {
  style: 'currency',
  currency: 'EUR',
  maximumFractionDigits: 2,
})

const text = computed(() => {
  const value = usage.value
  if (!value) return ''
  if (!value.cost_tracking) return 'Dépense IA non suivie (prix non configurés sur le serveur).'
  const spent = euros.format(value.month_cost_eur)
  if (value.budget_eur <= 0) return `Dépense IA ce mois-ci : ${spent}.`
  return `Dépense IA ce mois-ci : ${spent} sur ${euros.format(value.budget_eur)}.`
})

onMounted(async () => {
  try {
    usage.value = await api.usage()
  } catch {
    // Information secondaire : on n'affiche rien en cas d'erreur.
  }
})
</script>

<template>
  <span v-if="text" class="usage">{{ text }}</span>
</template>
