<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue'

const emit = defineEmits<{ photo: [file: File] }>()

const dialog = ref<HTMLDialogElement>()
const video = ref<HTMLVideoElement>()
const error = ref('')
let stream: MediaStream | undefined

/** Ouvre la caméra (arrière sur téléphone). Renvoie false si elle n'est pas utilisable ici. */
async function open(): Promise<void> {
  error.value = ''
  dialog.value?.showModal?.()
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'environment', width: { ideal: 2560 }, height: { ideal: 1440 } },
    })
    if (video.value) video.value.srcObject = stream
  } catch {
    error.value =
      'La caméra n’est pas disponible (accès refusé ou aucune caméra). ' +
      'Autorise-la dans ton navigateur, ou utilise « Photos des notes ».'
  }
}

function close(): void {
  stream?.getTracks().forEach((track) => track.stop())
  stream = undefined
  dialog.value?.close?.()
}

function shoot(): void {
  const view = video.value
  if (!view?.videoWidth) return
  const canvas = document.createElement('canvas')
  canvas.width = view.videoWidth
  canvas.height = view.videoHeight
  canvas.getContext('2d')?.drawImage(view, 0, 0)
  canvas.toBlob(
    (blob) => {
      if (!blob) return
      close()
      emit('photo', new File([blob], 'photo-camera.jpg', { type: 'image/jpeg' }))
    },
    'image/jpeg',
    0.92,
  )
}

onBeforeUnmount(close)
defineExpose({ open })
</script>

<template>
  <dialog ref="dialog" class="camera" aria-labelledby="camera-title" @close="close">
    <h2 id="camera-title">Prendre une photo</h2>
    <p v-if="error" class="message error" role="alert">{{ error }}</p>
    <video v-else ref="video" autoplay playsinline muted aria-label="Aperçu de la caméra" />
    <p class="camera-tip">Cadre bien ta page, bien éclairée, puis prends la photo.</p>
    <div class="actions">
      <button type="button" class="primary" :disabled="!!error" @click="shoot">
        Prendre la photo
      </button>
      <button type="button" class="ghost" @click="close">Annuler</button>
    </div>
  </dialog>
</template>

<style scoped>
.camera {
  width: min(40rem, calc(100vw - 2rem));
}
.camera-tip {
  color: var(--muted);
}
video {
  display: block;
  width: 100%;
  max-height: 60vh;
  background: #000;
  border-radius: var(--radius-sm);
}
</style>
