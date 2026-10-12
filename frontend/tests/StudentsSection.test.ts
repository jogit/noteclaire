import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import StudentsSection from '../src/components/StudentsSection.vue'

const lea = {
  id: 1,
  name: 'Léa',
  level: 'seconde',
  adaptation_codes: [],
  adaptation_notes: '',
  subject_ids: [1],
}
const tom = { ...lea, id: 2, name: 'Tom', level: 'premiere', subject_ids: [] }
const api = vi.hoisted(() => ({
  levels: vi.fn(),
  adaptations: vi.fn(),
  subjects: vi.fn(),
  students: vi.fn(),
  createStudent: vi.fn(),
  updateStudent: vi.fn(),
  setStudentSubjects: vi.fn(),
  deleteStudent: vi.fn(),
}))
vi.mock('../src/api/client', () => ({ api }))

async function mountSection() {
  const wrapper = mount(StudentsSection)
  await flushPromises()
  return wrapper
}

describe('StudentsSection', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.levels.mockResolvedValue([
      { id: 'seconde', name: 'Seconde' },
      { id: 'premiere', name: 'Première générale' },
    ])
    api.adaptations.mockResolvedValue([
      { id: 'dyslexie', name: 'Dyslexie' },
      { id: 'tdah', name: 'TDAH' },
    ])
    api.subjects.mockResolvedValue([
      { id: 1, name: 'Maths', slug: 'maths', usual_for: ['seconde', 'premiere'] },
      { id: 2, name: 'Latin', slug: 'latin', usual_for: [] },
    ])
    api.students.mockResolvedValue([lea, tom])
    api.updateStudent.mockResolvedValue(lea)
    api.setStudentSubjects.mockResolvedValue(lea)
  })

  it('présente chaque élève avec sa classe, ses matières et ses particularités', async () => {
    const wrapper = await mountSection()
    const cards = wrapper.findAll('.student-card')
    expect(cards).toHaveLength(2)
    expect((wrapper.find('#student-name-1').element as HTMLInputElement).value).toBe('Léa')
    expect((wrapper.find('#student-level-2').element as HTMLSelectElement).value).toBe('premiere')
    expect(cards[0].find('.chips').text()).toContain('Maths')
    expect(cards[1].text()).toContain('Aucune matière choisie.')
    expect(cards[0].text()).toContain('Aucune. L’IA s’en sert')
  })

  it('renomme et change la classe', async () => {
    const wrapper = await mountSection()
    await wrapper.find('#student-name-1').setValue('Léa M.')
    await wrapper.find('#student-name-1').trigger('change')
    expect(api.updateStudent).toHaveBeenCalledWith(1, { name: 'Léa M.' })

    await wrapper.find('#student-level-1').setValue('premiere')
    expect(api.updateStudent).toHaveBeenCalledWith(1, { level: 'premiere' })
  })

  it('coche une matière habituelle ou une autre matière', async () => {
    const wrapper = await mountSection()
    const card = wrapper.findAll('.student-card')[0]
    const usual = card.find('.picks').findAll('input')
    expect((usual[0].element as HTMLInputElement).checked).toBe(true)

    await card.find('.more .picks input').setValue(true)
    await flushPromises()
    expect(api.setStudentSubjects).toHaveBeenCalledWith(1, [1, 2])
  })

  it('enregistre les particularités cochées et la précision libre', async () => {
    const wrapper = await mountSection()
    await wrapper.find('.adaptation-options input').setValue(true)
    expect(api.updateStudent).toHaveBeenCalledWith(1, {
      adaptation_codes: ['dyslexie'],
      adaptation_notes: '',
    })

    await wrapper.find('#student-adapt-1-free').setValue('anxieux')
    await wrapper.find('#student-adapt-1-free').trigger('change')
    expect(api.updateStudent).toHaveBeenLastCalledWith(1, {
      adaptation_codes: [],
      adaptation_notes: 'anxieux',
    })
  })

  it('ajoute un élève', async () => {
    api.createStudent.mockResolvedValue({ ...lea, id: 3, name: 'Zoé' })
    const wrapper = await mountSection()
    await wrapper.find('#new-student-name').setValue('Zoé')
    await wrapper.find('.add-student form').trigger('submit')
    await flushPromises()
    expect(api.createStudent).toHaveBeenCalledWith('Zoé', 'seconde')
    expect((wrapper.find('#new-student-name').element as HTMLInputElement).value).toBe('')
  })

  it('supprime un autre élève après confirmation, jamais l’élève affiché', async () => {
    api.deleteStudent.mockResolvedValue(undefined)
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const wrapper = await mountSection()
    expect(wrapper.find('[aria-label="Supprimer Léa"]').exists()).toBe(false)

    await wrapper.find('[aria-label="Supprimer Tom"]').trigger('click')
    await flushPromises()
    expect(api.deleteStudent).toHaveBeenCalledWith(2)
  })

  it('affiche l’erreur du serveur', async () => {
    api.updateStudent.mockRejectedValue(new Error('boom'))
    const wrapper = await mountSection()
    await wrapper.find('#student-level-1').setValue('premiere')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').exists()).toBe(true)
  })
})
