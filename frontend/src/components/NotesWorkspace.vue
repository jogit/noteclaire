<script setup lang="ts">
import { Camera, Images, ImagePlus, ScanSearch, Video } from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { api } from '../api/client'
import { ApiError, errorMessage } from '../api/errors'
import { insertFigures, photoTextToNotes } from '../lib/notesFormat'
import AiProgress from './AiProgress.vue'
import CameraDialog from './CameraDialog.vue'
import NotesEditor from './NotesEditor.vue'
import PhotoViewer, { type ImportedPhoto } from './PhotoViewer.vue'
import SchemaList from './SchemaList.vue'

const props = defineProps<{ chapterId: number; modelValue: string }>()
const emit = defineEmits<{
  'update:modelValue': [value: string]
  typed: []
  captured: [wasEmpty: boolean]
}>()

const editor = ref<InstanceType<typeof NotesEditor>>()
const photos = ref<ImportedPhoto[]>([])
const storedPhotos = ref<ImportedPhoto[]>([])
const photoInput = ref<HTMLInputElement>()
const imageInput = ref<HTMLInputElement>()
const cameraInput = ref<HTMLInputElement>()
const camera = ref<InstanceType<typeof CameraDialog>>()
const reading = ref({ current: 0, total: 0 })
const uploading = ref(false)
const error = ref('')
// Lot de photos : combien sont lues, et lesquelles sont à réessayer (leçon sur plusieurs pages).
const imported = ref(0)
const failed = ref<{ file: File; message: string }[]>([])

const spotCount = computed(() => editor.value?.spots.length ?? 0)
const readingLabel = computed(() =>
  reading.value.total > 1
    ? `Lecture de la photo ${reading.value.current} sur ${reading.value.total}…`
    : 'Lecture de la photo…',
)

async function loadStoredPhotos(): Promise<void> {
  try {
    const list = await api.photos(props.chapterId)
    storedPhotos.value = list.map((photo, i) => ({ url: photo.url, name: `Photo ${i + 1}` }))
  } catch {
    // Les photos d'origine sont un confort : l'éditeur reste utilisable sans elles.
  }
}

function showStoredPhotos(): void {
  closePhotos()
  photos.value = [...storedPhotos.value]
}

function onPhotos(event: Event): Promise<void> {
  const files = [...((event.target as HTMLInputElement).files ?? [])]
  if (photoInput.value) photoInput.value.value = ''
  return files.length ? importPhotos(files) : Promise.resolve()
}

/** Caméra du navigateur ; sinon (connexion non sécurisée…) l'appareil photo du téléphone. */
function takePhoto(): void {
  if (navigator.mediaDevices && 'getUserMedia' in navigator.mediaDevices) camera.value?.open()
  else cameraInput.value?.click()
}

function onCameraFile(event: Event): void {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (cameraInput.value) cameraInput.value.value = ''
  if (file) importPhotos([file])
}

/** Lit les photos l'une après l'autre : chaque page s'ajoute à la suite des notes. */
async function importPhotos(files: File[]): Promise<void> {
  error.value = ''
  failed.value = []
  imported.value = 0
  reading.value = { current: 0, total: files.length }
  for (const [index, file] of files.entries()) {
    reading.value.current = index + 1
    // La photo reste dans le navigateur, pour comparer avec le texte lu.
    const photo = { url: URL.createObjectURL(file), name: file.name }
    photos.value.push(photo)
    try {
      const result = await api.photo(props.chapterId, file)
      emit('captured', !props.modelValue.trim())
      // Les schémas que l'IA a su découper remplacent leur « [schéma : …] » dans les notes.
      const text = insertFigures(result.text, result.figures ?? [])
      editor.value?.insertBlock(photoTextToNotes(text, result.uncertain))
      imported.value++
      loadStoredPhotos()
    } catch (e) {
      photos.value = photos.value.filter((p) => p.url !== photo.url)
      URL.revokeObjectURL(photo.url)
      failed.value.push({ file, message: errorMessage(e) })
      // Une photo illisible n'arrête pas les suivantes. Un problème qui ne vient pas de la photo
      // (IA indisponible, réseau, budget) arrêterait aussi les autres : on s'arrête là et on
      // garde le reste à réessayer.
      if (!(e instanceof ApiError && e.code.startsWith('photo_'))) {
        const rest = files.slice(index + 1)
        failed.value.push(
          ...rest.map((f) => ({ file: f, message: 'Pas lue : le lot s’est arrêté.' })),
        )
        break
      }
    }
  }
  reading.value = { current: 0, total: 0 }
}

/** Un schéma redessiné remplace la photo dans les notes, après accord de l'élève. */
function replaceImage(from: string, to: string): void {
  emit('update:modelValue', props.modelValue.split(from).join(to))
}

function retryFailed(): Promise<void> {
  return importPhotos(failed.value.map((f) => f.file))
}

async function addImage(file: Blob, name = 'schema.jpg'): Promise<void> {
  uploading.value = true
  error.value = ''
  try {
    const upload = file instanceof File ? file : new File([file], name, { type: 'image/jpeg' })
    const { url } = await api.uploadImage(props.chapterId, upload)
    editor.value?.insertImage(url, 'Schéma')
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    uploading.value = false
  }
}

function onImage(event: Event): void {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (imageInput.value) imageInput.value.value = ''
  if (file) addImage(file)
}

function closePhotos(): void {
  photos.value.forEach((photo) => {
    if (photo.url.startsWith('blob:')) URL.revokeObjectURL(photo.url)
  })
  photos.value = []
}

onBeforeUnmount(closePhotos)
onMounted(loadStoredPhotos)
</script>

<template>
  <div class="notes-workspace" :class="{ 'with-photo': photos.length }">
    <div class="notes-main">
      <p id="capture-label" class="group-label">Ajouter à mes notes</p>
      <div class="capture-tools" role="group" aria-labelledby="capture-label">
        <input
          :id="`notes-photo-${chapterId}`"
          ref="photoInput"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          multiple
          class="visually-hidden"
          :disabled="reading.total > 0"
          @change="onPhotos"
        />
        <label
          :for="`notes-photo-${chapterId}`"
          class="button-like"
          :aria-disabled="reading.total > 0"
        >
          <Camera :size="20" aria-hidden="true" />
          <span class="button-text">Photos des notes<small>lit l’écriture</small></span>
        </label>

        <input
          ref="cameraInput"
          type="file"
          accept="image/*"
          capture="environment"
          class="visually-hidden"
          tabindex="-1"
          aria-hidden="true"
          @change="onCameraFile"
        />
        <button type="button" class="button-like" :disabled="reading.total > 0" @click="takePhoto">
          <Video :size="20" aria-hidden="true" />
          <span class="button-text">Prendre une photo<small>avec la caméra</small></span>
        </button>
        <CameraDialog ref="camera" @photo="(file) => importPhotos([file])" />

        <input
          :id="`notes-image-${chapterId}`"
          ref="imageInput"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          class="visually-hidden"
          :disabled="uploading"
          @change="onImage"
        />
        <label :for="`notes-image-${chapterId}`" class="button-like" :aria-disabled="uploading">
          <ImagePlus :size="20" aria-hidden="true" />
          <span class="button-text">Image / schéma<small>garde l’image telle quelle</small></span>
        </label>

        <button v-if="storedPhotos.length" type="button" @click="showStoredPhotos">
          <Images :size="20" aria-hidden="true" /> Photos d'origine ({{ storedPhotos.length }})
        </button>
      </div>

      <p v-if="!reading.total && !imported && !failed.length" class="hint">
        Une leçon sur plusieurs pages ? Choisis toutes les photos d’un coup : chaque page s’ajoute à
        la suite de tes notes.
      </p>

      <AiProgress
        :key="reading.current"
        operation="photo"
        :running="reading.total > 0"
        :title="readingLabel"
      />
      <p v-if="imported && !reading.total" class="message success" role="status">
        {{ imported }} photo{{ imported > 1 ? 's lues' : ' lue' }} et ajoutée{{
          imported > 1 ? 's' : ''
        }}
        à tes notes.
      </p>
      <div v-if="failed.length && !reading.total" class="message warning" role="alert">
        <p>
          <strong>
            {{
              failed.length > 1
                ? `${failed.length} photos n’ont pas été lues`
                : 'Une photo n’a pas été lue'
            }}
          </strong>
        </p>
        <ul>
          <li v-for="(item, index) in failed" :key="`${item.file.name}-${index}`">
            {{ item.file.name }} : {{ item.message }}
          </li>
        </ul>
        <button type="button" class="secondary" @click="retryFailed">
          Réessayer {{ failed.length > 1 ? 'ces photos' : 'cette photo' }}
        </button>
      </div>
      <p v-if="uploading" class="hint" aria-live="polite">Ajout de l'image…</p>
      <p v-if="error" class="message error" role="alert">{{ error }}</p>

      <div v-if="spotCount" class="review-bar" role="status">
        <ScanSearch :size="20" aria-hidden="true" />
        <span>
          <strong>{{ spotCount }}</strong> passage{{ spotCount > 1 ? 's' : '' }} à vérifier avec ton
          cahier
        </span>
        <button type="button" class="primary" @click="editor?.nextSpot()">
          {{ spotCount > 1 ? 'Vérifier le suivant' : 'Vérifier' }}
        </button>
      </div>

      <SchemaList :chapter-id="chapterId" :notes="modelValue" @replace="replaceImage" />

      <NotesEditor
        ref="editor"
        :model-value="modelValue"
        @update:model-value="emit('update:modelValue', $event)"
        @typed="emit('typed')"
      />
    </div>

    <PhotoViewer
      v-if="photos.length"
      :photos="photos"
      @crop="addImage($event)"
      @close="closePhotos"
    />
  </div>
</template>
