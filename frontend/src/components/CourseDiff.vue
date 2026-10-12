<script setup lang="ts">
import { ArrowRight, CircleCheck, CircleMinus, CirclePlus, PenLine, Repeat } from 'lucide-vue-next'
import { computed } from 'vue'
import {
  ADDED_TEXT_WARNING_RATIO,
  compareNotesAndCourse,
  REMOVED_TEXT_WARNING_RATIO,
  summarizeChanges,
} from '../lib/textDiff'

const props = defineProps<{ notes: string; course: string }>()

const summary = computed(() => summarizeChanges(props.notes, props.course))
const full = computed(() => compareNotesAndCourse(props.notes, props.course))
const correctionCount = computed(() =>
  summary.value.corrections.reduce((total, change) => total + change.count, 0),
)
const nothingChanged = computed(
  () =>
    !summary.value.corrections.length &&
    !summary.value.rewrites.length &&
    !summary.value.added.length &&
    !summary.value.removed.length,
)
</script>

<template>
  <div class="changes">
    <p v-if="full.netAddedRatio > ADDED_TEXT_WARNING_RATIO" class="message warning" role="status">
      <span>
        <strong>⚠ Attention :</strong> le cours contient du texte absent de tes notes. Vérifie la
        liste « Ajouté » ci-dessous.
      </span>
    </p>
    <p
      v-if="full.netRemovedRatio > REMOVED_TEXT_WARNING_RATIO"
      class="message warning"
      role="status"
    >
      <span>
        <strong>⚠ Attention :</strong> une partie de tes notes a disparu du cours. Vérifie la liste
        « Retiré » ci-dessous.
      </span>
    </p>

    <div class="chips change-counts">
      <span class="chip done"
        ><PenLine :size="14" aria-hidden="true" /> {{ correctionCount }} correction{{
          correctionCount > 1 ? 's' : ''
        }}</span
      >
      <span v-if="summary.rewrites.length" class="chip info">
        <Repeat :size="14" aria-hidden="true" /> {{ summary.rewrites.length }} reformulation{{
          summary.rewrites.length > 1 ? 's' : ''
        }}
      </span>
      <span class="chip" :class="{ todo: summary.added.length }">
        <CirclePlus :size="14" aria-hidden="true" /> {{ summary.added.length }} ajout{{
          summary.added.length > 1 ? 's' : ''
        }}
      </span>
      <span class="chip" :class="{ todo: summary.removed.length }">
        <CircleMinus :size="14" aria-hidden="true" /> {{ summary.removed.length }} retrait{{
          summary.removed.length > 1 ? 's' : ''
        }}
      </span>
    </div>
    <p class="hint">
      + {{ summary.formatting }} retouche{{ summary.formatting > 1 ? 's' : '' }} de mise en forme
      (titres, ponctuation, majuscules, formules), sans effet sur le sens.
    </p>

    <div v-if="nothingChanged" class="empty-state">
      <CircleCheck :size="32" aria-hidden="true" />
      <strong>Rien n'a changé dans le contenu</strong>
      <span>Seule la mise en forme a été améliorée.</span>
    </div>

    <section v-if="summary.corrections.length" aria-labelledby="changes-corrections">
      <h3 id="changes-corrections">Fautes corrigées</h3>
      <ul class="change-list">
        <li v-for="change in summary.corrections" :key="change.before + change.after">
          <del>{{ change.before }}</del>
          <ArrowRight :size="16" aria-label="devient" />
          <ins>{{ change.after }}</ins>
          <span v-if="change.count > 1" class="hint">× {{ change.count }}</span>
        </li>
      </ul>
    </section>

    <section v-if="summary.added.length" aria-labelledby="changes-added">
      <h3 id="changes-added">Ajouté dans le cours <span class="hint">— à vérifier</span></h3>
      <p class="hint">
        Ces mots ne sont pas dans tes notes : vérifie qu'ils ne changent pas le sens.
      </p>
      <ul class="change-list">
        <li v-for="(text, index) in summary.added" :key="index">
          <ins>{{ text }}</ins>
        </li>
      </ul>
    </section>

    <section v-if="summary.removed.length" aria-labelledby="changes-removed">
      <h3 id="changes-removed">Retiré de tes notes <span class="hint">— à vérifier</span></h3>
      <p class="hint">Ces mots de tes notes ne se retrouvent pas dans le cours.</p>
      <ul class="change-list">
        <li v-for="(text, index) in summary.removed" :key="index">
          <del>{{ text }}</del>
        </li>
      </ul>
    </section>

    <section v-if="summary.rewrites.length" aria-labelledby="changes-rewrites">
      <h3 id="changes-rewrites">Reformulé</h3>
      <ul class="change-list">
        <li v-for="change in summary.rewrites" :key="change.before + change.after">
          <del>{{ change.before }}</del>
          <ArrowRight :size="16" aria-label="devient" />
          <ins>{{ change.after }}</ins>
        </li>
      </ul>
    </section>

    <details class="full-diff">
      <summary>Voir tout le texte annoté</summary>
      <p class="diff-legend">
        <del>Texte barré</del> : dans tes notes, retiré du cours. <ins>Texte souligné</ins> : ajouté
        dans le cours.
      </p>
      <p class="diff-text">
        <template v-for="(part, index) in full.parts" :key="index">
          <del v-if="part.kind === 'removed'">{{ part.text }}</del>
          <ins v-else-if="part.kind === 'added'">{{ part.text }}</ins>
          <span v-else>{{ part.text }}</span>
        </template>
      </p>
    </details>
  </div>
</template>
