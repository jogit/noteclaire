import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import SearchView from '../src/views/SearchView.vue'

const api = vi.hoisted(() => ({ search: vi.fn() }))
vi.mock('../src/api/client', () => ({ api }))
vi.mock('vue-router', async (importOriginal) => ({
  ...(await importOriginal<typeof import('vue-router')>()),
  useRoute: () => ({ query: { q: 'pente' } }),
}))

describe('SearchView', () => {
  it('affiche les résultats avec le mot cherché surligné, sans HTML injecté', async () => {
    api.search.mockResolvedValue([
      {
        chapter_id: 3,
        title: 'Fonctions affines',
        subject: 'Mathématiques',
        snippet: '<b>la</b> \u0002pente\u0003 est a',
      },
    ])
    const wrapper = mount(SearchView, { global: { stubs: { RouterLink: RouterLinkStub } } })
    await flushPromises()

    expect(api.search).toHaveBeenCalledWith('pente')
    expect(wrapper.find('mark').text()).toBe('pente')
    expect(wrapper.find('.snippet').text()).toContain('<b>la</b>')
    expect(wrapper.find('.snippet b').exists()).toBe(false)
  })
})
