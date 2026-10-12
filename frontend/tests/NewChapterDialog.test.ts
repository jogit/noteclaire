import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import NewChapterDialog from '../src/components/NewChapterDialog.vue'

const api = vi.hoisted(() => ({ subjects: vi.fn(), createChapter: vi.fn() }))
vi.mock('../src/api/client', () => ({ api }))

describe('NewChapterDialog', () => {
  it('crée le chapitre dans la matière choisie et l’ouvre', async () => {
    api.subjects.mockResolvedValue([
      { id: 1, name: 'Français', slug: 'francais' },
      { id: 6, name: 'SVT', slug: 'svt' },
    ])
    api.createChapter.mockResolvedValue({ id: 42 })
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', component: { template: '<div />' } },
        { path: '/chapitres/:id', name: 'chapter', component: { template: '<div />' } },
      ],
    })
    const wrapper = mount(NewChapterDialog, { global: { plugins: [router] } })

    await (wrapper.vm as unknown as { open: (id?: number) => Promise<void> }).open(6)
    await flushPromises()
    expect((wrapper.find('#new-chapter-subject').element as HTMLSelectElement).value).toBe('6')
    await wrapper.find('#new-chapter-name').setValue('La cellule')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(api.createChapter).toHaveBeenCalledWith(6, 'La cellule')
    expect(router.currentRoute.value.fullPath).toBe('/chapitres/42')
  })
})
