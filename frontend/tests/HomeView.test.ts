import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import HomeView from '../src/views/HomeView.vue'

const api = vi.hoisted(() => ({ chapters: vi.fn(), subjects: vi.fn(), usage: vi.fn() }))
vi.mock('../src/api/client', () => ({ api }))

const subjects = [
  { id: 1, name: 'Français', slug: 'francais', chapter_count: 0 },
  { id: 2, name: 'Mathématiques', slug: 'mathematiques', chapter_count: 2 },
]
const chapter = (id: number, progress: object) => ({
  id,
  title: `Chapitre ${id}`,
  subject_id: 2,
  subject: subjects[1],
  updated_at: new Date().toISOString(),
  progress: {
    notes_words: 10,
    course_version: null,
    notes_changed: false,
    pending_suggestions: 0,
    has_revision_sheet: false,
    has_quiz: false,
    ...progress,
  },
})

async function mountHome(openNewChapter = vi.fn()) {
  const wrapper = mount(HomeView, {
    global: {
      stubs: { RouterLink: RouterLinkStub },
      provide: { openNewChapter },
    },
  })
  await flushPromises()
  return wrapper
}

describe('HomeView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.subjects.mockResolvedValue(subjects)
    api.usage.mockResolvedValue({ month_cost_eur: 0, budget_eur: 5, cost_tracking: false })
  })

  it('montre les chapitres récents avec leur avancement et les matières', async () => {
    api.chapters.mockResolvedValue([
      chapter(1, { course_version: 2, pending_suggestions: 3, has_quiz: true }),
      chapter(2, {}),
    ])
    const wrapper = await mountHome()

    expect(wrapper.text()).toContain('1 chapitre attend d’être mis au propre')
    const cards = wrapper.findAll('.chapter-card')
    expect(cards).toHaveLength(2)
    expect(cards[0]!.text()).toContain('Cours prêt')
    expect(cards[0]!.text()).toContain('3 suggestions')
    expect(cards[0]!.text()).toContain('Quiz')
    expect(cards[1]!.text()).toContain('À mettre au propre')
    // Les matières utilisées d'abord ; celles sans chapitre se replient.
    expect(wrapper.findAll('.subject-card').map((c) => c.text())).toEqual([
      'Mathématiques2 chapitres',
      'FrançaisAucun chapitre',
    ])
    expect(wrapper.find('details.other-subjects summary').text()).toBe('Autres matières (1)')
  })

  it('accueille un premier lancement et ouvre la création de chapitre', async () => {
    api.chapters.mockResolvedValue([])
    api.subjects.mockResolvedValue(subjects.map((s) => ({ ...s, chapter_count: 0 })))
    const openNewChapter = vi.fn()
    const wrapper = await mountHome(openNewChapter)

    expect(wrapper.text()).toContain('Bienvenue dans NoteClaire')
    expect(wrapper.find('details.other-subjects').exists()).toBe(false) // tout est visible au départ
    expect(wrapper.findAll('.subject-card')).toHaveLength(2)
    await wrapper
      .findAll('button')
      .find((b) => b.text().includes('Créer mon premier chapitre'))!
      .trigger('click')
    expect(openNewChapter).toHaveBeenCalled()
  })
})
