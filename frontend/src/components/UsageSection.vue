<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../api/client'
import { errorMessage, messageForCode } from '../api/errors'
import type { OperationUsage, UsageDetails } from '../api/types'

const OPERATIONS: Record<string, string> = {
  structure: 'Mise au propre',
  analyze: 'Analyse',
  revision_sheet: 'Fiche de révision',
  quiz: 'Quiz',
  explain: "Je n'ai pas compris",
  photo: 'Photo des notes',
  figures: 'Découpe des schémas',
  redraw: 'Schéma redessiné',
}

const details = ref<UsageDetails>()
const period = ref<'last_7_days' | 'this_month'>('last_7_days')
const error = ref('')

const numbers = new Intl.NumberFormat('fr-FR')
const euros = new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' })
const dates = new Intl.DateTimeFormat('fr-FR', { dateStyle: 'short', timeStyle: 'short' })

const rows = computed<OperationUsage[]>(() => details.value?.[period.value] ?? [])
const totals = computed(() =>
  rows.value.reduce(
    (sum, row) => ({
      calls: sum.calls + row.calls,
      tokens: sum.tokens + row.input_tokens + row.output_tokens,
      cost: sum.cost + row.cost_eur,
    }),
    { calls: 0, tokens: 0, cost: 0 },
  ),
)

function label(operation: string): string {
  return OPERATIONS[operation] ?? operation
}

function seconds(ms: number): string {
  return `${numbers.format(Math.round(ms / 100) / 10)} s`
}

onMounted(async () => {
  try {
    details.value = await api.usageDetails()
  } catch (e) {
    error.value = errorMessage(e)
  }
})
</script>

<template>
  <section class="card" aria-labelledby="usage-title">
    <h2 id="usage-title">Consommation de l'IA</h2>
    <p v-if="error" class="message error" role="alert">{{ error }}</p>

    <template v-if="details">
      <p v-if="details.ai_provider === 'chatgpt'">
        NoteClaire compte ses propres appels ci-dessous. La jauge de ton abonnement (limite sur 5
        heures et sur la semaine) n'est visible que sur ChatGPT :
        <a :href="details.chatgpt_usage_url" target="_blank" rel="noopener">
          voir ma consommation ChatGPT
        </a>
        (c'est aussi là qu'on fixe une limite pour NoteClaire).
      </p>

      <div class="toolbar" role="group" aria-label="Période">
        <button
          type="button"
          class="secondary"
          :aria-pressed="period === 'last_7_days'"
          @click="period = 'last_7_days'"
        >
          7 derniers jours
        </button>
        <button
          type="button"
          class="secondary"
          :aria-pressed="period === 'this_month'"
          @click="period = 'this_month'"
        >
          Ce mois-ci
        </button>
      </div>

      <dl class="usage-totals">
        <div>
          <dt>Appels</dt>
          <dd>{{ numbers.format(totals.calls) }}</dd>
        </div>
        <div>
          <dt>Tokens</dt>
          <dd>{{ numbers.format(totals.tokens) }}</dd>
        </div>
        <div v-if="totals.cost > 0">
          <dt>Coût estimé</dt>
          <dd>{{ euros.format(totals.cost) }}</dd>
        </div>
      </dl>

      <p v-if="!rows.length">Aucun appel à l'IA sur cette période.</p>
      <table v-else class="usage-table">
        <thead>
          <tr>
            <th scope="col">Fonction</th>
            <th scope="col">Appels</th>
            <th scope="col">Échecs</th>
            <th scope="col">Tokens envoyés</th>
            <th scope="col">Tokens reçus</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.operation">
            <th scope="row">{{ label(row.operation) }}</th>
            <td>{{ numbers.format(row.calls) }}</td>
            <td>{{ numbers.format(row.errors) }}</td>
            <td>{{ numbers.format(row.input_tokens) }}</td>
            <td>{{ numbers.format(row.output_tokens) }}</td>
          </tr>
        </tbody>
      </table>

      <details v-if="details.recent.length" class="recent-runs">
        <summary>Derniers appels</summary>
        <ul>
          <li v-for="(run, index) in details.recent" :key="index">
            <span aria-hidden="true">{{ run.status === 'success' ? '✔ ' : '✘ ' }}</span>
            <span class="visually-hidden">{{
              run.status === 'success' ? 'Réussi :' : 'Échec :'
            }}</span>
            <strong>{{ label(run.operation) }}</strong>
            <span v-if="run.chapter_title"> — {{ run.chapter_title }}</span>
            <span class="hint">
              · {{ dates.format(new Date(run.created_at)) }} · {{ run.model }} ·
              {{ numbers.format(run.input_tokens + run.output_tokens) }} tokens ·
              {{ seconds(run.duration_ms) }}
            </span>
            <span v-if="run.status === 'error'" class="run-error">
              {{ messageForCode(run.error_code) }}
            </span>
          </li>
        </ul>
      </details>
    </template>
  </section>
</template>
