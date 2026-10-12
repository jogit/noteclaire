import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import SubjectsSection from '../src/components/SubjectsSection.vue'

const latin = { id: 1, name: 'Latin', slug: 'latin', enabled: true }
const api = vi.hoisted(() => ({
  subjects: vi.fn(),
  createSubject: vi.fn(),
  updateSubject: vi.fn(),
  deleteSubject: vi.fn(),
}))
vi.mock('../src/api/client', () => ({ api }))

describe('SubjectsSection', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.subjects.mockResolvedValue([latin])
  })

  it('ajoute et renomme une matière', async () => {
    api.createSubject.mockResolvedValue({ ...latin, id: 2, name: 'Grec' })
    api.updateSubject.mockResolvedValue(latin)
    const wrapper = mount(SubjectsSection)
    await flushPromises()
    expect(api.subjects).toHaveBeenCalledWith(true)

    await wrapper.find('#new-subject-name').setValue('Grec')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(api.createSubject).toHaveBeenCalledWith('Grec')

    await wrapper.find('#subject-name-1').setValue('Latin LCA')
    await wrapper.find('#subject-name-1').trigger('change')
    await flushPromises()
    expect(api.updateSubject).toHaveBeenCalledWith(1, { name: 'Latin LCA' })
  })

  it('affiche le refus de suppression', async () => {
    const { ApiError } = await import('../src/api/errors')
    api.deleteSubject.mockRejectedValue(new ApiError('subject_not_empty', 409))
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const wrapper = mount(SubjectsSection)
    await flushPromises()
    await wrapper.find('[aria-label^="Supprimer"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').exists()).toBe(true)
  })
})
