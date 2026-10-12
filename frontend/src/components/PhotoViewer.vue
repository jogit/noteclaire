<script setup lang="ts">
import { Crop, Minus, Plus, RotateCcw, X } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'

export interface ImportedPhoto {
  url: string
  name: string
}

const props = defineProps<{ photos: ImportedPhoto[] }>()
const emit = defineEmits<{ crop: [image: Blob]; close: [] }>()

const MAX_ZOOM = 6
const KEY_STEP = 40

const index = ref(0)
const cropping = ref(false)
const frame = ref<HTMLElement>()
const image = ref<HTMLImageElement>()
const selection = ref<{ x: number; y: number; w: number; h: number } | null>(null)
// Zoom et position de la photo dans son cadre (px d'écran, origine en haut à gauche).
const view = ref({ scale: 1, x: 0, y: 0 })
const dragging = ref(false)
const pointers = new Map<number, { x: number; y: number }>()
let origin: { x: number; y: number } | null = null
let pinch = 0

const photo = computed(() => props.photos[Math.min(index.value, props.photos.length - 1)])
const zoomed = computed(() => view.value.scale > 1)
const stageStyle = computed(() => ({
  transform: `translate(${view.value.x}px, ${view.value.y}px) scale(${view.value.scale})`,
}))

/** Garde la photo dans le cadre : on ne peut pas la perdre hors de l'écran. */
function place(scale: number, x: number, y: number): void {
  const box = frame.value
  const img = image.value
  const s = Math.min(Math.max(scale, 1), MAX_ZOOM)
  const minX = box && img ? Math.min(0, box.clientWidth - img.clientWidth * s) : 0
  const minY = box && img ? Math.min(0, box.clientHeight - img.clientHeight * s) : 0
  view.value = { scale: s, x: Math.min(Math.max(x, minX), 0), y: Math.min(Math.max(y, minY), 0) }
}

function reset(): void {
  view.value = { scale: 1, x: 0, y: 0 }
}

/** Change le zoom en gardant fixe le point (px, py) du cadre (la souris, ou le centre). */
function zoomAt(factor: number, px: number, py: number): void {
  const { scale, x, y } = view.value
  const next = Math.min(Math.max(scale * factor, 1), MAX_ZOOM)
  place(next, px - ((px - x) * next) / scale, py - ((py - y) * next) / scale)
}

function zoomCenter(factor: number): void {
  const box = frame.value
  if (box) zoomAt(factor, box.clientWidth / 2, box.clientHeight / 2)
}

function frameXY(event: { clientX: number; clientY: number }): { x: number; y: number } {
  const rect = frame.value!.getBoundingClientRect()
  return { x: event.clientX - rect.left, y: event.clientY - rect.top }
}

/** Position dans la photo (px de la photo à taille normale), pour tracer la zone à découper. */
function imageXY(event: PointerEvent): { x: number; y: number } {
  const img = image.value!
  const p = frameXY(event)
  const { scale, x, y } = view.value
  return {
    x: Math.min(Math.max((p.x - x) / scale, 0), img.clientWidth),
    y: Math.min(Math.max((p.y - y) / scale, 0), img.clientHeight),
  }
}

function onWheel(event: WheelEvent): void {
  const p = frameXY(event)
  zoomAt(Math.exp(-event.deltaY * 0.0015), p.x, p.y)
}

function spread(): number {
  const [a, b] = [...pointers.values()]
  return Math.hypot(a!.x - b!.x, a!.y - b!.y)
}

function onDown(event: PointerEvent): void {
  ;(event.currentTarget as HTMLElement).setPointerCapture?.(event.pointerId)
  pointers.set(event.pointerId, frameXY(event))
  if (pointers.size === 2) {
    pinch = spread()
    origin = null
    selection.value = null
  } else if (cropping.value) {
    origin = imageXY(event)
    selection.value = { ...origin, w: 0, h: 0 }
  } else {
    dragging.value = true
  }
}

function onMove(event: PointerEvent): void {
  const last = pointers.get(event.pointerId)
  if (!last) return
  const now = frameXY(event)
  pointers.set(event.pointerId, now)
  if (pointers.size === 2) {
    const next = spread()
    const [a, b] = [...pointers.values()]
    if (pinch > 0) zoomAt(next / pinch, (a!.x + b!.x) / 2, (a!.y + b!.y) / 2)
    pinch = next
  } else if (origin) {
    const p = imageXY(event)
    selection.value = {
      x: Math.min(origin.x, p.x),
      y: Math.min(origin.y, p.y),
      w: Math.abs(p.x - origin.x),
      h: Math.abs(p.y - origin.y),
    }
  } else if (dragging.value) {
    place(view.value.scale, view.value.x + now.x - last.x, view.value.y + now.y - last.y)
  }
}

function onUp(event: PointerEvent): void {
  pointers.delete(event.pointerId)
  if (pointers.size < 2) pinch = 0
  if (pointers.size === 0) dragging.value = false
  origin = null
}

function onDoubleClick(event: MouseEvent): void {
  if (cropping.value) return
  const p = frameXY(event)
  if (zoomed.value) reset()
  else zoomAt(2.5, p.x, p.y)
}

function onKey(event: KeyboardEvent): void {
  const { scale, x, y } = view.value
  const moves: Record<string, [number, number]> = {
    ArrowLeft: [KEY_STEP, 0],
    ArrowRight: [-KEY_STEP, 0],
    ArrowUp: [0, KEY_STEP],
    ArrowDown: [0, -KEY_STEP],
  }
  if (event.key === '+' || event.key === '=') zoomCenter(1.4)
  else if (event.key === '-') zoomCenter(1 / 1.4)
  else if (event.key === '0') reset()
  else if (moves[event.key]) place(scale, x + moves[event.key]![0], y + moves[event.key]![1])
  else return
  event.preventDefault()
}

function startCrop(): void {
  cropping.value = true
  selection.value = null
}

watch(index, reset)

/** Découpe la zone choisie dans la photo d'origine (pleine résolution). */
function confirmCrop(): void {
  const img = image.value
  const zone = selection.value
  if (!img || !zone || zone.w < 10 || zone.h < 10) return
  const scale = img.naturalWidth / img.clientWidth
  const canvas = document.createElement('canvas')
  canvas.width = Math.round(zone.w * scale)
  canvas.height = Math.round(zone.h * scale)
  canvas
    .getContext('2d')
    ?.drawImage(
      img,
      zone.x * scale,
      zone.y * scale,
      canvas.width,
      canvas.height,
      0,
      0,
      canvas.width,
      canvas.height,
    )
  canvas.toBlob(
    (blob) => {
      if (blob) emit('crop', blob)
    },
    'image/jpeg',
    0.9,
  )
  cropping.value = false
  selection.value = null
}
</script>

<template>
  <aside class="photo-viewer" aria-label="Photo des notes">
    <div class="section-header">
      <h3>Photo des notes</h3>
      <button type="button" class="icon ghost" aria-label="Fermer la photo" @click="emit('close')">
        <X :size="20" aria-hidden="true" />
      </button>
    </div>

    <div v-if="photos.length > 1" class="photo-tabs" role="tablist" aria-label="Photos">
      <button
        v-for="(item, i) in photos"
        :key="item.url"
        type="button"
        role="tab"
        :aria-selected="i === index"
        @click="index = i"
      >
        Page {{ i + 1 }}
      </button>
    </div>

    <div
      v-if="photo"
      ref="frame"
      class="photo-frame"
      :class="{ cropping, dragging, zoomed }"
      tabindex="0"
      role="group"
      aria-label="Photo : molette ou + et - pour zoomer, glisser ou flèches pour déplacer"
      @wheel.prevent="onWheel"
      @pointerdown="onDown"
      @pointermove="onMove"
      @pointerup="onUp"
      @pointercancel="onUp"
      @dblclick="onDoubleClick"
      @keydown="onKey"
    >
      <div class="photo-stage" :style="stageStyle">
        <img
          ref="image"
          :src="photo.url"
          :alt="`Photo des notes : ${photo.name}`"
          draggable="false"
        />
        <div
          v-if="selection"
          class="crop-zone"
          :style="{
            left: `${selection.x}px`,
            top: `${selection.y}px`,
            width: `${selection.w}px`,
            height: `${selection.h}px`,
          }"
        />
      </div>
    </div>

    <p v-if="!cropping && photo" class="hint">
      Molette pour zoomer, glisse pour déplacer, double-clic pour agrandir.
    </p>
    <p v-if="cropping" class="hint">
      Trace un rectangle autour du schéma avec la souris ou le doigt (molette ou deux doigts pour
      zoomer).
    </p>
    <div class="toolbar">
      <template v-if="!cropping">
        <button type="button" class="secondary" @click="startCrop">
          <Crop :size="18" aria-hidden="true" /> Découper un schéma
        </button>
        <button type="button" class="ghost" aria-label="Zoom arrière" @click="zoomCenter(1 / 1.4)">
          <Minus :size="18" aria-hidden="true" />
        </button>
        <button type="button" class="ghost" aria-label="Zoom avant" @click="zoomCenter(1.4)">
          <Plus :size="18" aria-hidden="true" />
        </button>
        <button type="button" class="ghost" :disabled="!zoomed" @click="reset">
          <RotateCcw :size="18" aria-hidden="true" /> Taille normale
        </button>
      </template>
      <template v-else>
        <button
          type="button"
          class="primary"
          :disabled="!selection || selection.w < 10 || selection.h < 10"
          @click="confirmCrop"
        >
          Ajouter ce schéma aux notes
        </button>
        <button type="button" class="ghost" @click="cropping = false">Annuler</button>
        <button type="button" class="ghost" aria-label="Zoom avant" @click="zoomCenter(1.4)">
          <Plus :size="18" aria-hidden="true" />
        </button>
        <button type="button" class="ghost" aria-label="Zoom arrière" @click="zoomCenter(1 / 1.4)">
          <Minus :size="18" aria-hidden="true" />
        </button>
      </template>
    </div>
  </aside>
</template>
