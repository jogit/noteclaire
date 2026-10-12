import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../src/api/errors'
import type { Suggestion } from '../src/api/types'
import SuggestionCard from '../src/components/SuggestionCard.vue'

const api = vi.hoisted(() => ({ acceptSuggestion: vi.fn(), rejectSuggestion: vi.fn() }))
vi.mock('../src/api/client', () => ({ api }))

const suggestion = (overrides: Partial<Suggestion> = {}): Suggestion => ({
  id: 7,
  chapter_id: 1,
  type: 'correction',
  original_text: 'b est la pente',
  suggested_text: 'a est le coefficient directeur',
  reason: 'La définition semble inversée.',
  confidence: 0.9,
  status: 'pending',
  created_at: '2026-10-03T20:00:00Z',
  decided_at: null,
  source_reference: '',
  ...overrides,
})

const buttons = (wrapper: ReturnType<typeof mount>) => wrapper.findAll('button')

describe('SuggestionCard', () => {
  beforeEach(() => vi.clearAllMocks())

  it('affiche le texte noté, la suggestion, la raison et la confiance', () => {
    const wrapper = mount(SuggestionCard, { props: { suggestion: suggestion() } })
    expect(wrapper.text()).toContain('Correction proposée')
    expect(wrapper.text()).toContain('b est la pente')
    expect(wrapper.text()).toContain('La définition semble inversée.')
    expect(wrapper.text()).not.toContain('Confiance')
    expect(buttons(wrapper).map((b) => b.text())).toEqual(['Accepter', 'Refuser'])
  })

  it('signale un complément absent des notes', () => {
    const wrapper = mount(SuggestionCard, {
      props: { suggestion: suggestion({ type: 'addition', confidence: 0.4 }) },
    })
    expect(wrapper.text()).toContain('Pas dans tes notes')
    expect(wrapper.text()).toContain("L'IA n'en est pas sûre")
    expect(buttons(wrapper).map((b) => b.text())).toEqual(['Ajouter', 'Ignorer'])
  })

  it('émet le nouveau cours après acceptation', async () => {
    const course = { version: 2 }
    api.acceptSuggestion.mockResolvedValue({ suggestion: {}, course })
    const wrapper = mount(SuggestionCard, { props: { suggestion: suggestion() } })

    await buttons(wrapper)[0]!.trigger('click')
    await flushPromises()

    expect(api.acceptSuggestion).toHaveBeenCalledWith(7, undefined)
    expect(wrapper.emitted('decided')).toEqual([[7, course]])
  })

  it('fait choisir le passage quand il apparaît plusieurs fois', async () => {
    api.acceptSuggestion
      .mockRejectedValueOnce(
        new ApiError('suggestion_ambiguous', 409, '', {
          occurrences: [
            { index: 0, before: 'x ', match: 'b est la pente', after: ' y' },
            { index: 1, before: 'z ', match: 'b est la pente', after: ' w' },
          ],
        }),
      )
      .mockResolvedValueOnce({ suggestion: {}, course: { version: 2 } })
    const wrapper = mount(SuggestionCard, { props: { suggestion: suggestion() } })

    await buttons(wrapper)[0]!.trigger('click')
    await flushPromises()
    const choices = wrapper.findAll('button.occurrence')
    expect(choices).toHaveLength(2)

    await choices[1]!.trigger('click')
    await flushPromises()
    expect(api.acceptSuggestion).toHaveBeenLastCalledWith(7, 1)
    expect(wrapper.emitted('decided')).toHaveLength(1)
  })

  it('propose de recopier une suggestion devenue obsolète', async () => {
    api.acceptSuggestion.mockRejectedValue(new ApiError('suggestion_outdated', 409))
    const wrapper = mount(SuggestionCard, { props: { suggestion: suggestion() } })

    await buttons(wrapper)[0]!.trigger('click')
    await flushPromises()

    expect(wrapper.find('.copy-text').text()).toBe('a est le coefficient directeur')
  })

  it('refuse sans toucher au cours', async () => {
    api.rejectSuggestion.mockResolvedValue({})
    const wrapper = mount(SuggestionCard, { props: { suggestion: suggestion() } })

    await buttons(wrapper)[1]!.trigger('click')
    await flushPromises()

    expect(wrapper.emitted('decided')).toEqual([[7, null]])
  })

  it('cite le document de référence utilisé', () => {
    const wrapper = mount(SuggestionCard, {
      props: { suggestion: suggestion({ source_reference: 'Programme de seconde' }) },
    })
    expect(wrapper.find('.source').text()).toContain("D'après : Programme de seconde")
  })
})

describe('SuggestionCard — complément', () => {
  it('cite le passage avec ses formules rendues, sans Markdown brut', () => {
    const wrapper = mount(SuggestionCard, {
      props: {
        suggestion: suggestion({
          type: 'addition',
          original_text: 'On voit entre $400\\ \\mathrm{nm}$ et $800\\ \\mathrm{nm}$.',
          suggested_text: 'Un rayonnement monochromatique a une seule longueur d’onde.',
        }),
      },
    })
    const excerpt = wrapper.find('.excerpt')
    expect(excerpt.findAll('.katex')).toHaveLength(2)
    expect(excerpt.text()).not.toContain('$')
  })
})
