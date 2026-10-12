import { ref } from 'vue'
import { api } from '../api/client'
import type { Subject } from '../api/types'

/** Matières partagées par le menu et les pages (avec le nombre de chapitres). */
const subjects = ref<Subject[]>([])
let loading: Promise<void> | undefined

async function refresh(): Promise<void> {
  loading = api
    .subjects()
    .then((list) => {
      subjects.value = list
    })
    .finally(() => {
      loading = undefined
    })
  return loading
}

export function useSubjects() {
  return {
    subjects,
    refresh,
    ensureLoaded: () => (subjects.value.length ? Promise.resolve() : (loading ?? refresh())),
    bySlug: (slug: string) => subjects.value.find((s) => s.slug === slug),
  }
}
