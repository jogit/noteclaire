import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import StudySection from '../src/components/StudySection.vue'

const api = vi.hoisted(() => ({
  revisionSheet: vi.fn(),
  quiz: vi.fn(),
  createRevisionSheet: vi.fn(),
  createQuiz: vi.fn(),
  quizAnkiUrl: (id: number) => `/api/chapters/${id}/quiz/anki.txt`,
}))
vi.mock('../src/api/client', () => ({ api }))

const sheet = {
  chapter_id: 1,
  content_markdown: '# À retenir\n\n- point',
  course_version: 2,
  outdated: false,
  created_at: '2026-10-03T20:00:00Z',
}

async function mountSection() {
  const wrapper = mount(StudySection, {
    props: { chapterId: 1, courseVersion: 2 },
    global: { stubs: { RouterLink: RouterLinkStub } },
  })
  await flushPromises()
  return wrapper
}

describe('StudySection', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.revisionSheet.mockResolvedValue(null)
    api.quiz.mockResolvedValue(null)
  })

  it('crée une fiche de révision et propose de l’imprimer', async () => {
    api.createRevisionSheet.mockResolvedValue(sheet)
    const wrapper = await mountSection()

    await wrapper.findAll('button')[0]!.trigger('click')
    await flushPromises()

    expect(wrapper.find('.sheet h1').text()).toBe('À retenir')
    const link = wrapper.findComponent(RouterLinkStub)
    expect(link.props('to')).toEqual({
      name: 'print',
      params: { id: 1 },
      query: { quoi: 'fiche' },
    })
  })

  it('signale une fiche faite sur une ancienne version du cours', async () => {
    api.revisionSheet.mockResolvedValue({ ...sheet, outdated: true })
    const wrapper = await mountSection()
    expect(wrapper.text()).toContain('Le cours a changé depuis cette fiche')
  })

  it('affiche les erreurs de génération', async () => {
    const { ApiError } = await import('../src/api/errors')
    api.createQuiz.mockRejectedValue(new ApiError('ai_budget_exceeded', 429))
    const wrapper = await mountSection()

    await wrapper.findAll('button')[1]!.trigger('click')
    await flushPromises()

    expect(wrapper.find('[role="alert"]').text()).toContain('budget IA du mois est atteint')
  })

  it('propose l’export du quiz pour Anki seulement quand un quiz existe', async () => {
    let wrapper = await mountSection()
    expect(wrapper.find('.anki').exists()).toBe(false)

    api.quiz.mockResolvedValue({
      chapter_id: 1,
      course_version: 2,
      outdated: false,
      created_at: '2026-10-03T20:00:00Z',
      questions: [
        {
          type: 'short',
          question: 'Que vaut f(0) ?',
          choices: [],
          answer: '1',
          explanation: 'b = 1',
          course_excerpt: 'f(0) = 1',
        },
      ],
    })
    wrapper = await mountSection()
    const link = wrapper.find('.anki a')
    expect(link.attributes('href')).toBe('/api/chapters/1/quiz/anki.txt')
    expect(link.attributes('download')).toBeDefined()
    expect(wrapper.find('.anki').text()).toContain('Fichier → Importer')
  })
})
