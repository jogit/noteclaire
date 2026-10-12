import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import TrashView from '../src/views/TrashView.vue'

const push = vi.fn()
const api = vi.hoisted(() => ({
  trash: vi.fn(),
  restoreChapter: vi.fn(),
  purgeChapter: vi.fn(),
  subjects: vi.fn(),
}))
vi.mock('../src/api/client', () => ({ api }))
vi.mock('vue-router', async (importOriginal) => ({
  ...(await importOriginal<typeof import('vue-router')>()),
  useRouter: () => ({ push }),
}))

const item = {
  id: 4,
  title: 'Vecteurs',
  subject: { id: 2, name: 'Mathématiques', slug: 'mathematiques' },
  deleted_at: '2026-10-03T20:00:00Z',
  expires_at: '2026-11-02T20:00:00Z',
}

describe('TrashView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.trash.mockResolvedValue([item])
    api.subjects.mockResolvedValue([])
  })

  it('récupère un chapitre et l’ouvre', async () => {
    api.restoreChapter.mockResolvedValue({})
    const wrapper = mount(TrashView)
    await flushPromises()
    expect(wrapper.text()).toContain('Vecteurs')
    expect(wrapper.text()).toContain('2 novembre')

    await wrapper.find('button.primary').trigger('click')
    await flushPromises()
    expect(api.restoreChapter).toHaveBeenCalledWith(4)
    expect(push).toHaveBeenCalledWith({ name: 'chapter', params: { id: 4 } })
  })

  it('n’efface définitivement qu’après confirmation', async () => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
    const wrapper = mount(TrashView)
    await flushPromises()
    await wrapper.find('[aria-label="Effacer définitivement Vecteurs"]').trigger('click')
    expect(api.purgeChapter).not.toHaveBeenCalled()

    confirm.mockReturnValue(true)
    await wrapper.find('[aria-label="Effacer définitivement Vecteurs"]').trigger('click')
    await flushPromises()
    expect(api.purgeChapter).toHaveBeenCalledWith(4)
    expect(wrapper.text()).toContain('La corbeille est vide.')
  })
})
