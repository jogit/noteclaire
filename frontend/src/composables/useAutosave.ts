import { onBeforeUnmount, ref } from 'vue'

export type SaveStatus = 'saved' | 'pending' | 'saving' | 'error'

/**
 * Sauvegarde automatique après quelques secondes d'inactivité (SPEC §22).
 * `flush()` force la sauvegarde immédiate (avant mise au propre, avant de quitter la page).
 */
export function useAutosave(save: (keepalive: boolean) => Promise<void>, delayMs = 1500) {
  const status = ref<SaveStatus>('saved')
  let timer: ReturnType<typeof setTimeout> | undefined
  let running: Promise<void> | undefined
  let dirty = false

  async function run(keepalive = false): Promise<void> {
    clearTimeout(timer)
    timer = undefined
    if (running) await running.catch(() => {})
    if (!dirty) return
    dirty = false
    status.value = 'saving'
    running = save(keepalive)
      .then(() => {
        status.value = dirty ? 'pending' : 'saved'
      })
      .catch((error: unknown) => {
        dirty = true
        status.value = 'error'
        throw error
      })
      .finally(() => {
        running = undefined
      })
    await running
  }

  function schedule(): void {
    dirty = true
    status.value = 'pending'
    clearTimeout(timer)
    timer = setTimeout(() => {
      run().catch(() => {})
    }, delayMs)
  }

  onBeforeUnmount(() => clearTimeout(timer))

  return {
    status,
    schedule,
    flush: (keepalive = false) => run(keepalive),
    hasUnsavedChanges: () => dirty || running !== undefined,
  }
}
