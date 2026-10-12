import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import PrintView from '../src/views/PrintView.vue'

const api = vi.hoisted(() => ({ chapter: vi.fn(), course: vi.fn(), revisionSheet: vi.fn() }))
const query = vi.hoisted(() => ({ value: {} as Record<string, string> }))
vi.mock('../src/api/client', () => ({ api }))
vi.mock('vue-router', async (importOriginal) => ({
  ...(await importOriginal<typeof import('vue-router')>()),
  useRoute: () => ({ query: query.value }),
}))

describe('PrintView', () => {
  afterEach(() => vi.restoreAllMocks())

  it('affiche titre, matière, date et cours puis lance l’impression', async () => {
    api.chapter.mockResolvedValue({
      title: 'Fonctions affines',
      subject: { name: 'Mathématiques', slug: 'mathematiques' },
    })
    api.course.mockResolvedValue({ content_markdown: '# Cours\n\n$f(x)=ax+b$', version: 3 })
    const print = vi.spyOn(window, 'print').mockImplementation(() => {})
    query.value = {}

    const wrapper = mount(PrintView, { props: { id: '1' } })
    await flushPromises()

    expect(wrapper.find('.print-title').text()).toBe('Fonctions affines')
    expect(wrapper.find('.print-subject').text()).toBe('Mathématiques')
    expect(wrapper.find('.print-meta').text()).toContain('Cours · version 3')
    expect(wrapper.find('.katex').exists()).toBe(true)
    expect(print).toHaveBeenCalled()
  })

  it('imprime la fiche de révision', async () => {
    api.chapter.mockResolvedValue({ title: 'T', subject: { name: 'SVT', slug: 'svt' } })
    api.revisionSheet.mockResolvedValue({ content_markdown: '# Fiche', course_version: 1 })
    vi.spyOn(window, 'print').mockImplementation(() => {})
    query.value = { quoi: 'fiche', auto: '0' }

    const wrapper = mount(PrintView, { props: { id: '1' } })
    await flushPromises()

    expect(wrapper.find('.print-meta').text()).toContain('Fiche de révision')
    expect(window.print).not.toHaveBeenCalled()
  })
})
