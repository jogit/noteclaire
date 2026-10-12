import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({ adaptations: vi.fn() }))
vi.mock('../src/api/client', () => ({ api }))

describe('loadAdaptations', () => {
  beforeEach(() => {
    vi.resetModules() // le cache est dans le module : on repart d'un module neuf
    api.adaptations.mockReset()
  })

  it('ne demande la liste qu’une fois', async () => {
    api.adaptations.mockResolvedValue([{ id: 'dyslexie', name: 'Dyslexie' }])
    const { loadAdaptations } = await import('../src/lib/adaptations')
    const [a, b] = await Promise.all([loadAdaptations(), loadAdaptations()])
    expect(a).toEqual(b)
    expect(api.adaptations).toHaveBeenCalledTimes(1)
  })

  it('réessaie à l’appel suivant après un échec', async () => {
    api.adaptations.mockRejectedValueOnce(new Error('réseau'))
    api.adaptations.mockResolvedValueOnce([{ id: 'tdah', name: 'TDAH' }])
    const { loadAdaptations } = await import('../src/lib/adaptations')
    await expect(loadAdaptations()).rejects.toThrow('réseau')
    expect(await loadAdaptations()).toEqual([{ id: 'tdah', name: 'TDAH' }])
  })
})
