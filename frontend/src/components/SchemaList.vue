<script setup lang="ts">
import { PencilRuler } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { api } from '../api/client'
import { errorMessage } from '../api/errors'
import AiProgress from './AiProgress.vue'

const props = defineProps<{ chapterId: number; notes: string }>()
const emit = defineEmits<{ replace: [from: string, to: string] }>()

// Les schémas photographiés du chapitre (les schémas déjà redessinés sont des .svg : ignorés).
const IMAGE = /!\[([^\]\n]*)\]\((\/api\/images\/\d+\/[0-9a-f]{32}\.jpg)\)/g

const schemas = computed(() =>
  [...props.notes.matchAll(IMAGE)].map((m) => ({ alt: m[1] || 'Schéma', url: m[2]! })),
)
const redrawing = ref('')
const proposal = ref<{ from: string; to: string; corrections: string[] }>()
const error = ref('')
const remark = ref('')
const hand = ref(false)

/** Change l'aspect (propre / écrit à la main) de la version proposée, sans rappeler l'IA. */
async function restyle(): Promise<void> {
  const current = proposal.value
  if (!current) return
  error.value = ''
  try {
    const { url } = await api.restyleSchema(props.chapterId, current.to, hand.value)
    proposal.value = { ...current, to: url }
  } catch (e) {
    error.value = errorMessage(e)
  }
}

/** Une première fois, ou (avec la remarque de l'élève) pour corriger la version proposée. */
async function redraw(url: string, correction = false): Promise<void> {
  const previous = correction ? proposal.value : undefined
  redrawing.value = url
  error.value = ''
  try {
    const asked = previous ? { previousUrl: previous.to, remark: remark.value.trim() } : undefined
    proposal.value = undefined
    const redrawn = await api.redrawSchema(props.chapterId, url, asked)
    const shown = hand.value ? await api.restyleSchema(props.chapterId, redrawn.url, true) : redrawn
    proposal.value = { from: url, to: shown.url, corrections: redrawn.corrections }
    remark.value = ''
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    redrawing.value = ''
  }
}

function accept(): void {
  if (proposal.value) emit('replace', proposal.value.from, proposal.value.to)
  proposal.value = undefined
}
</script>

<template>
  <section v-if="schemas.length" class="schemas" aria-label="Schémas de tes notes">
    <h3>Schémas de tes notes</h3>
    <p v-if="error" class="message error" role="alert">{{ error }}</p>
    <ul>
      <li v-for="schema in schemas" :key="schema.url">
        <img :src="schema.url" :alt="schema.alt" loading="lazy" />
        <div class="schema-actions">
          <span class="schema-caption">{{ schema.alt }}</span>
          <button
            type="button"
            class="secondary"
            :disabled="!!redrawing"
            :aria-label="`Redessiner proprement : ${schema.alt}`"
            @click="redraw(schema.url)"
          >
            <PencilRuler :size="18" aria-hidden="true" /> Redessiner proprement
          </button>
        </div>

        <AiProgress
          v-if="redrawing === schema.url"
          operation="redraw"
          :running="true"
          title="Redessin du schéma"
        />

        <div
          v-if="proposal?.from === schema.url"
          class="schema-compare"
          role="group"
          aria-label="Comparaison"
        >
          <figure>
            <img :src="proposal.from" alt="Ta photo" />
            <figcaption>Ta photo</figcaption>
          </figure>
          <figure>
            <img :src="proposal.to" alt="Schéma redessiné" />
            <figcaption>Schéma propre</figcaption>
          </figure>
          <label class="hand-option">
            <input v-model="hand" type="checkbox" @change="restyle" />
            Aspect écrit à la main
          </label>
          <div v-if="proposal.corrections.length" class="corrections" role="note">
            <strong>L’IA a repéré quelque chose :</strong>
            <ul>
              <li v-for="note in proposal.corrections" :key="note">{{ note }}</li>
            </ul>
          </div>
          <p class="hint">Vérifie que tout est bien recopié, surtout les mots écrits à la main.</p>
          <form class="schema-remark" @submit.prevent="redraw(proposal.from, true)">
            <label :for="`remark-${chapterId}`"
              >Quelque chose ne va pas ? Dis-le (facultatif)</label
            >
            <div class="remark-row">
              <input
                :id="`remark-${chapterId}`"
                v-model="remark"
                type="text"
                maxlength="500"
                placeholder="Ex. : il manque la pointe de la flèche « état » à gauche"
              />
              <button type="submit" class="secondary" :disabled="!remark.trim() || !!redrawing">
                Corriger le schéma
              </button>
            </div>
          </form>
          <div class="schema-actions">
            <button type="button" class="primary" @click="accept">Utiliser le schéma propre</button>
            <button type="button" class="ghost" @click="proposal = undefined">
              Garder ma photo
            </button>
          </div>
        </div>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.schemas h3 {
  margin: 1rem 0 0.5rem;
  font-size: 1rem;
}
.schemas ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.75rem;
}
.schemas li {
  min-width: 0;
  display: grid;
  gap: 0.5rem;
  padding: 0.75rem;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
}
.schemas li > img {
  max-height: 8rem;
  max-width: 100%;
  object-fit: contain;
  justify-self: start;
}
.schema-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1rem;
  align-items: center;
}
.schema-caption {
  color: var(--muted);
}
.schema-compare {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}
.schema-compare figure {
  min-width: 0;
  margin: 0;
  display: grid;
  gap: 0.25rem;
}
.schema-compare img {
  display: block;
  width: 100%;
  height: auto;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
}
.corrections {
  padding: 0.5rem 0.75rem;
  border-left: 4px solid var(--warning, #b26a00);
  background: var(--surface-2, transparent);
}
.corrections ul {
  margin: 0.25rem 0 0;
  padding-left: 1.25rem;
}
.remark-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.remark-row input {
  flex: 1 1 18rem;
}
@media (max-width: 640px) {
  .schema-compare {
    grid-template-columns: 1fr;
  }
}
.schema-compare p,
.schema-compare .hand-option,
.schema-compare .corrections,
.schema-compare .schema-actions,
.schema-compare .schema-remark {
  grid-column: 1 / -1;
}
.schema-compare p {
  margin: 0;
}
</style>
