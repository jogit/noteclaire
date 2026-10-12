import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ChapterHeader from '../src/components/ChapterHeader.vue'

const api = vi.hoisted(() => ({
  renameChapter: vi.fn(),
  deleteChapter: vi.fn(),
  exportMarkdownUrl: (id: number) => `/api/chapters/${id}/export.md`,
}))
vi.mock('../src/api/client', () => ({ api }))

const chapter = {
  id: 4,
  subject_id: 2,
  subject: { id: 2, name: 'Mathématiques', slug: 'mathematiques' },
  title: 'Fonctions affines',
  description: '',
  school_year: '',
  created_at: '2026-10-01T10:00:00Z',
  updated_at: '2026-10-01T10:00:00Z',
}

function mountHeader(hasCourse = true) {
  return mount(ChapterHeader, {
    props: { chapter, hasCourse },
    global: { stubs: { RouterLink: RouterLinkStub } },
  })
}

const openMenu = (wrapper: ReturnType<typeof mountHeader>) =>
  wrapper.find('[aria-label="Plus d\'actions"]').trigger('click')
const item = (wrapper: ReturnType<typeof mountHeader>, text: string) =>
  wrapper.findAll('.menu-panel button').find((b) => b.text().includes(text))!

describe('ChapterHeader', () => {
  beforeEach(() => vi.clearAllMocks())

  it('affiche la matière et le titre', () => {
    const wrapper = mountHeader()
    expect(wrapper.find('h1').text()).toBe('Fonctions affines')
    expect(wrapper.find('.subject-chip').text()).toContain('Mathématiques')
  })

  it('renomme le chapitre et prévient le parent', async () => {
    api.renameChapter.mockResolvedValue({ ...chapter, title: 'Droites' })
    const wrapper = mountHeader()
    await openMenu(wrapper)
    await item(wrapper, 'Renommer').trigger('click')
    await wrapper.find('#rename').setValue('  Droites ')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(api.renameChapter).toHaveBeenCalledWith(4, 'Droites')
    expect(wrapper.emitted('renamed')).toEqual([[{ ...chapter, title: 'Droites' }]])
    expect(wrapper.find('form').exists()).toBe(false)
  })

  it('garde le formulaire ouvert et signale l’erreur si le renommage échoue', async () => {
    api.renameChapter.mockRejectedValue(new Error('boom'))
    const wrapper = mountHeader()
    await openMenu(wrapper)
    await item(wrapper, 'Renommer').trigger('click')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.emitted('error')).toHaveLength(1)
    expect(wrapper.find('form').exists()).toBe(true)
  })

  it('ne supprime qu’après confirmation', async () => {
    api.deleteChapter.mockResolvedValue(undefined)
    const confirm = vi.spyOn(window, 'confirm')
    const wrapper = mountHeader()

    confirm.mockReturnValueOnce(false)
    await openMenu(wrapper)
    await item(wrapper, 'Supprimer').trigger('click')
    expect(api.deleteChapter).not.toHaveBeenCalled()

    confirm.mockReturnValueOnce(true)
    await openMenu(wrapper)
    await item(wrapper, 'Supprimer').trigger('click')
    await flushPromises()
    expect(api.deleteChapter).toHaveBeenCalledWith(4)
    expect(wrapper.emitted('deleted')).toHaveLength(1)
  })

  it('propose les exports seulement quand le chapitre a un cours', async () => {
    const without = mountHeader(false)
    await openMenu(without)
    expect(without.find('.menu-panel').text()).not.toContain('Markdown')

    const withCourse = mountHeader(true)
    await openMenu(withCourse)
    expect(withCourse.find('.menu-panel a[download]').attributes('href')).toBe(
      '/api/chapters/4/export.md',
    )
  })
})
