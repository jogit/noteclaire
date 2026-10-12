import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import UsageSection from '../src/components/UsageSection.vue'

const api = vi.hoisted(() => ({ usageDetails: vi.fn() }))
vi.mock('../src/api/client', () => ({ api }))

const row = (operation: string, calls: number, tokens: number) => ({
  operation,
  calls,
  errors: 0,
  input_tokens: tokens,
  output_tokens: tokens,
  cost_eur: 0,
})

describe('UsageSection', () => {
  it('résume les appels par période et renvoie vers la jauge ChatGPT', async () => {
    api.usageDetails.mockResolvedValue({
      ai_provider: 'chatgpt',
      last_7_days: [row('structure', 2, 1000), row('quiz', 1, 500)],
      this_month: [row('structure', 5, 4000)],
      recent: [
        {
          created_at: '2026-10-04T07:10:00Z',
          operation: 'structure',
          chapter_title: 'vecteur',
          provider: 'chatgpt',
          model: 'gpt-5.5',
          status: 'error',
          error_code: 'ai_timeout',
          input_tokens: 0,
          output_tokens: 0,
          duration_ms: 1200,
        },
      ],
      chatgpt_usage_url: 'https://chatgpt.com/settings/usage',
    })
    const wrapper = mount(UsageSection)
    await flushPromises()

    expect(wrapper.find('a').attributes('href')).toBe('https://chatgpt.com/settings/usage')
    expect(wrapper.find('.usage-totals').text().replace(/\s/g, '')).toContain('Appels3')
    expect(wrapper.find('.usage-totals').text().replace(/\s/g, '')).toContain('Tokens3000')
    expect(wrapper.find('.usage-table').text()).toContain('Mise au propre')
    expect(wrapper.find('.usage-totals').text()).not.toContain('Coût')

    await wrapper
      .findAll('button')
      .find((b) => b.text() === 'Ce mois-ci')!
      .trigger('click')
    expect(wrapper.find('.usage-totals').text().replace(/\s/g, '')).toContain('Appels5')

    expect(wrapper.find('.recent-runs').text()).toContain('vecteur')
    expect(wrapper.find('.run-error').text()).toContain('trop de temps')
  })
})
