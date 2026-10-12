<script setup lang="ts">
import { Download, HardDriveDownload, RotateCcw } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import { api } from '../api/client'
import { errorMessage } from '../api/errors'
import type { Backup } from '../api/types'
import { timeAgo } from '../lib/time'

const backups = ref<Backup[]>([])
const busy = ref(false)
const error = ref('')
const message = ref('')

const dateFormat = new Intl.DateTimeFormat('fr-FR', { dateStyle: 'full', timeStyle: 'short' })

function size(bytes: number): string {
  return bytes >= 1024 * 1024
    ? `${(bytes / 1024 / 1024).toFixed(1).replace('.', ',')} Mo`
    : `${Math.max(1, Math.round(bytes / 1024))} Ko`
}

async function load(): Promise<void> {
  try {
    backups.value = await api.backups()
  } catch (e) {
    error.value = errorMessage(e)
  }
}

async function backupNow(): Promise<void> {
  busy.value = true
  error.value = ''
  message.value = ''
  try {
    await api.createBackup()
    message.value = 'Sauvegarde faite.'
    await load()
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    busy.value = false
  }
}

const RESTORE_WARNING =
  'Remplacer tous les chapitres, notes et images actuels par cette sauvegarde ? ' +
  'Une copie de l’état actuel est faite avant, pour pouvoir revenir en arrière.'

async function restore(action: () => Promise<void>): Promise<void> {
  if (!window.confirm(RESTORE_WARNING)) return
  busy.value = true
  error.value = ''
  try {
    await action()
    window.location.assign('/') // tout l'affichage dépend des données : on repart de zéro
  } catch (e) {
    error.value = errorMessage(e)
    busy.value = false
  }
}

function restoreOne(name: string): Promise<void> {
  return restore(() => api.restoreBackup(name))
}

function restoreFromFile(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  return file ? restore(() => api.restoreBackupFile(file)) : Promise.resolve()
}

onMounted(load)
</script>

<template>
  <section class="card" aria-labelledby="backup-title">
    <div class="section-header">
      <h2 id="backup-title">Sauvegardes</h2>
      <button type="button" class="secondary" :disabled="busy" @click="backupNow">
        <HardDriveDownload :size="18" aria-hidden="true" />
        {{ busy ? 'Sauvegarde…' : 'Sauvegarder maintenant' }}
      </button>
    </div>
    <p class="hint">
      Chaque jour, NoteClaire copie automatiquement tous les chapitres et leurs images dans le
      dossier
      <code>backups/</code>. Les 7 dernières sauvegardes sont gardées. Pour plus de sécurité,
      télécharge-en une de temps en temps sur une clé USB ou un autre ordinateur.
    </p>
    <p v-if="message" class="message success" role="status">{{ message }}</p>
    <p v-if="error" class="message error" role="alert">{{ error }}</p>

    <p v-if="!backups.length && !error" class="empty-hint">Aucune sauvegarde pour l’instant.</p>
    <ul v-else class="item-list">
      <li v-for="backup in backups" :key="backup.name">
        <div>
          <strong>{{ timeAgo(backup.created_at) }}</strong>
          <span class="chapter-subject">
            {{ dateFormat.format(new Date(backup.created_at)) }} — {{ size(backup.size) }}
          </span>
        </div>
        <div class="row-actions">
          <a class="button-like" :href="api.backupUrl(backup.name)" :download="backup.name">
            <Download :size="18" aria-hidden="true" /> Télécharger
          </a>
          <button type="button" class="secondary" :disabled="busy" @click="restoreOne(backup.name)">
            <RotateCcw :size="18" aria-hidden="true" /> Restaurer
          </button>
        </div>
      </li>
    </ul>

    <p class="hint">
      Pour reprendre des données d’une autre installation, choisis un fichier de sauvegarde
      téléchargé plus tôt :
    </p>
    <label class="button-like restore-file" :aria-disabled="busy">
      <RotateCcw :size="18" aria-hidden="true" /> Restaurer depuis un fichier…
      <input
        type="file"
        accept=".zip,application/zip"
        class="visually-hidden"
        :disabled="busy"
        @change="restoreFromFile"
      />
    </label>
  </section>
</template>

<style scoped>
.row-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.restore-file {
  cursor: pointer;
}
</style>
