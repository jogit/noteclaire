import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useAutosave } from '../src/composables/useAutosave'

vi.mock('vue', async (importOriginal) => ({
  ...(await importOriginal<typeof import('vue')>()),
  onBeforeUnmount: () => {},
}))

describe('useAutosave', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  it("sauvegarde une seule fois après la période d'inactivité", async () => {
    const save = vi.fn().mockResolvedValue(undefined)
    const autosave = useAutosave(save, 1000)

    autosave.schedule()
    await vi.advanceTimersByTimeAsync(500)
    autosave.schedule()
    expect(autosave.status.value).toBe('pending')
    await vi.advanceTimersByTimeAsync(999)
    expect(save).not.toHaveBeenCalled()

    await vi.advanceTimersByTimeAsync(1)
    expect(save).toHaveBeenCalledTimes(1)
    expect(autosave.status.value).toBe('saved')
  })

  it('flush sauvegarde immédiatement et ne fait rien sans modification', async () => {
    const save = vi.fn().mockResolvedValue(undefined)
    const autosave = useAutosave(save, 1000)

    await autosave.flush()
    expect(save).not.toHaveBeenCalled()

    autosave.schedule()
    await autosave.flush()
    expect(save).toHaveBeenCalledTimes(1)
    await vi.advanceTimersByTimeAsync(2000)
    expect(save).toHaveBeenCalledTimes(1)
  })

  it("garde les modifications en cas d'erreur pour réessayer", async () => {
    const save = vi.fn().mockRejectedValueOnce(new Error('réseau')).mockResolvedValue(undefined)
    const autosave = useAutosave(save, 1000)

    autosave.schedule()
    await expect(autosave.flush()).rejects.toThrow('réseau')
    expect(autosave.status.value).toBe('error')
    expect(autosave.hasUnsavedChanges()).toBe(true)

    await autosave.flush()
    expect(save).toHaveBeenCalledTimes(2)
    expect(autosave.status.value).toBe('saved')
  })
})
