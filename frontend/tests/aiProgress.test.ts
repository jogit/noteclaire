import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import AiProgress from '../src/components/AiProgress.vue'
import { estimatedProgress, refreshDurations, stageIndex } from '../src/lib/aiProgress'

const api = vi.hoisted(() => ({ aiDurations: vi.fn() }))
vi.mock('../src/api/client', () => ({ api }))

describe('estimatedProgress', () => {
  it('atteint 90 % à la durée habituelle et ne dépasse jamais 98 %', () => {
    expect(estimatedProgress(0, 20)).toBe(0)
    expect(estimatedProgress(10, 20)).toBeGreaterThan(0.6)
    expect(estimatedProgress(20, 20)).toBeCloseTo(0.9)
    expect(estimatedProgress(40, 20)).toBeLessThan(0.98)
    expect(estimatedProgress(10_000, 20)).toBeLessThanOrEqual(0.98)
  })

  it('avance toujours', () => {
    let previous = 0
    for (let t = 1; t < 120; t++) {
      const value = estimatedProgress(t, 15)
      expect(value).toBeGreaterThan(previous)
      previous = value
    }
  })

  it('répartit les étapes sur la durée estimée', () => {
    expect(stageIndex(0, 4)).toBe(0)
    expect(stageIndex(0.3, 4)).toBe(1)
    expect(stageIndex(0.68, 4)).toBe(2)
    expect(stageIndex(0.86, 4)).toBe(3)
  })
})

describe('AiProgress', () => {
  afterEach(() => {
    vi.useRealTimers()
    refreshDurations()
  })

  it('affiche le pourcentage estimé, l’étape et le temps restant, puis 100 %', async () => {
    vi.useFakeTimers()
    api.aiDurations.mockResolvedValue({ structure: 10 })
    const wrapper = mount(AiProgress, {
      props: { operation: 'structure', running: true, title: 'Mise au propre' },
    })
    await flushPromises()
    await vi.advanceTimersByTimeAsync(5000)

    const bar = wrapper.find('[role="progressbar"]')
    const value = Number(bar.attributes('aria-valuenow'))
    expect(value).toBeGreaterThan(50)
    expect(value).toBeLessThan(90)
    expect(wrapper.text()).toContain('Mise au propre')
    expect(wrapper.text()).toMatch(/Environ \d+ s/)
    expect(wrapper.text()).not.toContain('Lecture de tes notes') // étape déjà passée

    await wrapper.setProps({ running: false })
    expect(bar.attributes('aria-valuenow')).toBe('100')
    expect(wrapper.text()).toContain('Terminé')
    await vi.advanceTimersByTimeAsync(700)
    expect(wrapper.find('.ai-progress').exists()).toBe(false)
  })

  it('utilise une durée par défaut si le serveur ne répond pas', async () => {
    vi.useFakeTimers()
    api.aiDurations.mockRejectedValue(new Error('hors ligne'))
    const wrapper = mount(AiProgress, { props: { operation: 'quiz', running: true } })
    await flushPromises()
    await vi.advanceTimersByTimeAsync(1000)
    expect(
      Number(wrapper.find('[role="progressbar"]').attributes('aria-valuenow')),
    ).toBeGreaterThan(0)
  })
})
