import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ReferencesView from '../src/views/ReferencesView.vue'

const api = vi.hoisted(() => ({
  levels: vi.fn(),
  students: vi.fn(),
  subjects: vi.fn(),
  references: vi.fn(),
  uploadReference: vi.fn(),
  deleteReference: vi.fn(),
  syncReferences: vi.fn(),
  downloadProgrammes: vi.fn(),
}))
vi.mock('../src/api/client', () => ({ api }))

const subjects = [
  { id: 1, name: 'Français', slug: 'francais' },
  { id: 2, name: 'Mathématiques', slug: 'mathematiques' },
]
const programme = {
  id: 9,
  subject_id: 2,
  title: 'Programme de maths',
  source: 'Bulletin officiel',
  url: 'https://example.org/maths.pdf',
  school_year: '',
  file_path: 'seconde/mathematiques/programme.pdf',
  chunk_count: 42,
  updated_at: '2026-10-03T20:00:00Z',
}

async function mountView() {
  const wrapper = mount(ReferencesView)
  await flushPromises()
  return wrapper
}

const button = (wrapper: Awaited<ReturnType<typeof mountView>>, text: string) =>
  wrapper.findAll('button').find((b) => b.text().includes(text))!

describe('ReferencesView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.levels.mockResolvedValue([{ id: 'seconde', name: 'Seconde' }])
    api.students.mockResolvedValue([
      {
        id: 1,
        name: 'Léa',
        level: 'seconde',
        adaptation_codes: [],
        adaptation_notes: '',
        subject_ids: [],
      },
    ])
    api.subjects.mockResolvedValue(subjects)
    api.references.mockResolvedValue([programme])
  })

  it('présente les documents de la classe de l’élève, groupés par matière', async () => {
    const wrapper = await mountView()
    expect(wrapper.find('header').text()).toContain('Léa')
    expect(wrapper.find('header').text()).toContain('Seconde')
    expect(wrapper.find('.group h2').text()).toBe('Mathématiques')
    expect(wrapper.text()).toContain('Programme de maths')
    expect(wrapper.text()).toContain('Bulletin officiel')
    expect(wrapper.find('a[href="https://example.org/maths.pdf"]').exists()).toBe(true)
  })

  it('guide vers le téléchargement quand il n’y a aucun document', async () => {
    api.references.mockResolvedValue([])
    const wrapper = await mountView()
    expect(wrapper.find('.empty').text()).toContain('Télécharger les programmes officiels')
  })

  it('télécharge les programmes officiels et signale les échecs', async () => {
    api.downloadProgrammes.mockResolvedValue({
      downloaded: 9,
      already: 0,
      errors: ['Programme de maths : téléchargement impossible (404)'],
    })
    const wrapper = await mountView()
    await button(wrapper, 'Télécharger les programmes officiels').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('9 programme(s) téléchargé(s).')
    expect(wrapper.find('.message.warning').text()).toContain('téléchargement impossible')
    expect(api.references.mock.calls.length).toBeGreaterThan(1)
  })

  it('envoie un document personnel avec sa matière et ses métadonnées', async () => {
    api.uploadReference.mockResolvedValue({ ...programme, title: 'Fiche' })
    const wrapper = await mountView()
    const file = new File(['contenu'], 'fiche.md', { type: 'text/markdown' })
    const input = wrapper.find('#ref-file')
    Object.defineProperty(input.element, 'files', { value: [file] })
    await input.trigger('change')
    await wrapper.find('#ref-subject').setValue(2)
    await wrapper.find('#ref-source').setValue('Manuel')
    await wrapper.find('.advanced-form').trigger('submit')
    await flushPromises()

    expect(api.uploadReference).toHaveBeenCalledWith(2, file, {
      title: '',
      source: 'Manuel',
      url: '',
    })
    expect(wrapper.text()).toContain('« Fiche » a été ajouté.')
  })

  it('supprime un document après confirmation', async () => {
    api.deleteReference.mockResolvedValue(undefined)
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const wrapper = await mountView()
    await wrapper.find('[aria-label="Supprimer Programme de maths"]').trigger('click')
    await flushPromises()
    expect(api.deleteReference).toHaveBeenCalledWith(9)
  })

  it('affiche les erreurs de lecture du dossier', async () => {
    api.syncReferences.mockResolvedValue({
      added: 0,
      updated: 0,
      removed: 0,
      unchanged: 1,
      errors: ['inconnue/doc.md : matière inconnue'],
    })
    const wrapper = await mountView()
    await button(wrapper, 'Relire le dossier').trigger('click')
    await flushPromises()
    expect(wrapper.find('.message.warning').text()).toContain('matière inconnue')
  })
})
