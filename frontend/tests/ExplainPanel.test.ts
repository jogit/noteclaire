import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import ExplainPanel from '../src/components/ExplainPanel.vue'

const api = vi.hoisted(() => ({ explain: vi.fn() }))
vi.mock('../src/api/client', () => ({ api }))

describe('ExplainPanel', () => {
  it('explique tout de suite le passage, sans autre clic', async () => {
    api.explain.mockResolvedValue({ text: 'La pente dit de combien monte la droite.', answer: '' })
    const wrapper = mount(ExplainPanel, { props: { chapterId: 4, passage: 'a est la pente' } })
    await flushPromises()

    expect(api.explain).toHaveBeenCalledWith(4, 'a est la pente', 'simpler')
    expect(wrapper.text()).toContain('La pente dit de combien monte la droite.')
  })

  it('pose une question de vérification et cache la réponse', async () => {
    api.explain.mockResolvedValue({ text: 'Que vaut $a$ ?', answer: 'Le coefficient directeur.' })
    const wrapper = mount(ExplainPanel, { props: { chapterId: 4, passage: 'a est la pente' } })

    await wrapper
      .findAll('button')
      .find((b) => b.text() === 'Une question')!
      .trigger('click')
    await flushPromises()

    expect(api.explain).toHaveBeenCalledWith(4, 'a est la pente', 'question')
    expect(wrapper.find('.katex').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('Le coefficient directeur.')
    await wrapper
      .findAll('button')
      .find((b) => b.text() === 'Voir la réponse')!
      .trigger('click')
    expect(wrapper.text()).toContain('Le coefficient directeur.')
    expect(wrapper.text()).toContain("n'est pas ajoutée à ton cours")
  })

  it('affiche les erreurs', async () => {
    const { ApiError } = await import('../src/api/errors')
    api.explain.mockRejectedValue(new ApiError('ai_not_configured', 503))
    const wrapper = mount(ExplainPanel, { props: { chapterId: 4, passage: 'x' } })

    await wrapper.findAll('button')[1]!.trigger('click')
    await flushPromises()

    expect(wrapper.find('[role="alert"]').text()).toContain("L'IA n'est pas configurée")
  })
})
