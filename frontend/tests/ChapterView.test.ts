import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { suggestion } from './fixtures'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'
import type { Course } from '../src/api/types'
import ChapterView from '../src/views/ChapterView.vue'

const calls: string[] = []

const course = (overrides: Partial<Course> = {}): Course => ({
  chapter_id: 1,
  content_markdown: '# Fonctions affines\n\nSoit $f(x) = ax + b$.',
  version: 1,
  origin: 'ai_structure',
  created_at: '2026-10-03T20:00:00Z',
  notes_changed: false,
  has_manual_changes: false,
  title: 'Fonctions affines',
  ...overrides,
})

const api = vi.hoisted(() => ({
  chapter: vi.fn(),
  notes: vi.fn(),
  course: vi.fn(),
  saveNotes: vi.fn(),
  structure: vi.fn(),
  pendingSuggestions: vi.fn(),
  analyze: vi.fn(),
  references: vi.fn(),
  revisionSheet: vi.fn(),
  quiz: vi.fn(),
  deleteChapter: vi.fn(),
  renameChapter: vi.fn(),
  photo: vi.fn(),
  subjects: vi.fn(),
  noteVersions: vi.fn(),
  noteVersion: vi.fn(),
  restoreNoteVersion: vi.fn(),
  exportMarkdownUrl: (id: number) => `/api/chapters/${id}/export.md`,
}))

vi.mock('../src/api/client', () => ({ api }))

async function mountChapter(query = '') {
  const router: Router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'home', component: { template: '<div />' } },
      { path: '/matieres/:slug', name: 'subject', component: { template: '<div />' } },
      { path: '/chapitres/:id', name: 'chapter', component: ChapterView, props: true },
      { path: '/chapitres/:id/imprimer', name: 'print', component: { template: '<div />' } },
    ],
  })
  await router.push(`/chapitres/1${query}`)
  await router.isReady()
  const wrapper = mount(
    { template: '<RouterView />' },
    {
      global: { plugins: [router], stubs: { NotesWorkspace: NotesWorkspaceStub } },
      attachTo: document.body,
    },
  )
  await flushPromises()
  return { wrapper, router }
}

const NotesWorkspaceStub = {
  name: 'NotesWorkspace',
  props: ['modelValue', 'chapterId'],
  emits: ['update:modelValue', 'typed', 'captured'],
  template:
    '<textarea class="notes-stub" :value="modelValue" ' +
    "@input=\"$emit('update:modelValue', $event.target.value); $emit('typed')\" />",
}

const tab = (wrapper: Awaited<ReturnType<typeof mountChapter>>['wrapper'], label: string) =>
  wrapper.findAll('[role="tab"]').find((t) => t.text().includes(label))!

describe('ChapterView', () => {
  beforeEach(() => {
    calls.length = 0
    vi.clearAllMocks()
    document.body.innerHTML = ''
    api.chapter.mockResolvedValue({
      id: 1,
      title: 'Fonctions affines',
      subject_id: 2,
      subject: { id: 2, name: 'Mathématiques', slug: 'mathematiques' },
      progress: { pending_suggestions: 2 },
    })
    api.notes.mockResolvedValue({ raw_text: 'f(x)=ax+b', source: 'keyboard' })
    api.course.mockResolvedValue(null)
    api.pendingSuggestions.mockResolvedValue([])
    api.references.mockResolvedValue([])
    api.revisionSheet.mockResolvedValue(null)
    api.quiz.mockResolvedValue(null)
    api.subjects.mockResolvedValue([])
    api.saveNotes.mockImplementation(async () => calls.push('save'))
    api.structure.mockImplementation(async () => {
      calls.push('structure')
      return course()
    })
  })

  it('ouvre les notes tant que le cours n’est pas prêt', async () => {
    const { wrapper } = await mountChapter()
    expect(tab(wrapper, 'Mes notes').attributes('aria-selected')).toBe('true')
    expect(wrapper.find('h1').text()).toBe('Fonctions affines')
    expect(wrapper.find('.subject-chip').text()).toContain('Mathématiques')
    expect(wrapper.text()).toContain('Ton cours propre apparaîtra ici')
  })

  it('sauvegarde les notes, met au propre, affiche le cours et le fait relire', async () => {
    api.analyze.mockImplementation(async () => {
      calls.push('analyze')
      return [suggestion(5, { original_text: 'Fonctions affines' })]
    })
    const { wrapper, router } = await mountChapter()
    await wrapper.find('.notes-stub').setValue('f(x)=ax+b\nb ordonnée')

    await wrapper.find('button.big').trigger('click')
    await flushPromises()

    expect(calls).toEqual(['save', 'structure', 'analyze'])
    expect(api.saveNotes).toHaveBeenCalledWith(1, 'f(x)=ax+b\nb ordonnée', 'keyboard', {
      keepalive: false,
      checkpoint: undefined,
    })
    expect(router.currentRoute.value.query.onglet).toBe('cours')
    expect(tab(wrapper, 'Mon cours').attributes('aria-selected')).toBe('true')
    expect(wrapper.find('#panel-cours .markdown h1').text()).toBe('Fonctions affines')
    expect(wrapper.find('#panel-cours .katex').exists()).toBe(true)
    expect(wrapper.find('button.big').text()).toContain('Remettre le cours au propre')
    // Le point relevé par la relecture est surligné dans le cours et compté sur l'onglet.
    expect(wrapper.find('#panel-cours .course-review-bar').text()).toContain('1 point à regarder')
    expect(tab(wrapper, 'Mon cours').find('.badge-count').text()).toContain('1')
  })

  it("affiche l'erreur de l'IA sans perdre les notes", async () => {
    const { ApiError } = await import('../src/api/errors')
    api.structure.mockRejectedValue(new ApiError('ai_timeout', 504))
    const { wrapper } = await mountChapter()

    await wrapper.find('button.big').trigger('click')
    await flushPromises()

    expect(wrapper.find('[role="alert"]').text()).toContain('trop de temps')
    expect((wrapper.find('.notes-stub').element as HTMLTextAreaElement).value).toBe('f(x)=ax+b')
  })

  it('ouvre le cours par défaut et signale les notes modifiées', async () => {
    api.course.mockResolvedValue(course({ notes_changed: true }))
    const { wrapper } = await mountChapter()
    expect(tab(wrapper, 'Mon cours').attributes('aria-selected')).toBe('true')
    expect(tab(wrapper, 'Mes notes').find('.warning-dot').exists()).toBe(true)
    expect(wrapper.text()).toContain('Tes notes ont changé depuis la dernière mise au propre')
  })

  it('montre le nombre de suggestions en attente sur l’onglet', async () => {
    api.course.mockResolvedValue(course())
    api.pendingSuggestions.mockResolvedValue([suggestion(1), suggestion(2), suggestion(3)])
    const { wrapper } = await mountChapter()
    expect(tab(wrapper, 'Mon cours').find('.badge-count').text()).toContain('3')
    expect(wrapper.findAll('[role="tab"]')).toHaveLength(3)
  })

  it('change d’onglet', async () => {
    api.course.mockResolvedValue(course())
    const { wrapper, router } = await mountChapter()
    await tab(wrapper, 'Réviser').trigger('click')
    await vi.waitFor(() => expect(router.currentRoute.value.query.onglet).toBe('reviser'))
  })

  it('demande confirmation avant de remettre au propre un cours retouché', async () => {
    api.course.mockResolvedValue(course({ has_manual_changes: true, origin: 'user_edit' }))
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
    const { wrapper } = await mountChapter('?onglet=notes')

    await wrapper.find('button.big').trigger('click')
    await flushPromises()

    expect(confirm).toHaveBeenCalledWith(expect.stringContaining('historique'))
    expect(api.structure).not.toHaveBeenCalled()
    confirm.mockRestore()
  })

  it('demande confirmation s’il reste des passages à vérifier', async () => {
    api.notes.mockResolvedValue({
      raw_text: 'la [?cellule|celule] est [illisible]',
      source: 'photo',
    })
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
    const { wrapper } = await mountChapter()

    await wrapper.find('button.big').trigger('click')
    await flushPromises()

    expect(confirm).toHaveBeenCalledWith(expect.stringContaining('2 passages à vérifier'))
    expect(api.structure).not.toHaveBeenCalled()
    confirm.mockRestore()
  })

  it('sauvegarde toute modification venant de l’éditeur (vérification, schéma…)', async () => {
    const { wrapper } = await mountChapter()
    wrapper
      .findComponent({ name: 'NotesWorkspace' })
      .vm.$emit('update:modelValue', 'f(x)=ax+b corrigé')
    await new Promise((resolve) => setTimeout(resolve, 1600))
    expect(api.saveNotes).toHaveBeenLastCalledWith(1, 'f(x)=ax+b corrigé', 'keyboard', {
      keepalive: false,
      checkpoint: undefined,
    })
  })

  it('note la source quand les notes viennent d’une photo', async () => {
    api.notes.mockResolvedValue({ raw_text: '', source: 'keyboard' })
    const { wrapper } = await mountChapter()
    const workspace = wrapper.findComponent({ name: 'NotesWorkspace' })
    workspace.vm.$emit('captured', true)
    workspace.vm.$emit('update:modelValue', 'texte lu sur la photo')
    await new Promise((resolve) => setTimeout(resolve, 1600))
    expect(api.saveNotes).toHaveBeenLastCalledWith(1, 'texte lu sur la photo', 'photo', {
      keepalive: false,
      checkpoint: 'photo',
    })
  })

  it('garde une version des notes juste après l’import d’une photo', async () => {
    const { wrapper } = await mountChapter()
    const workspace = wrapper.findComponent({ name: 'NotesWorkspace' })
    workspace.vm.$emit('captured', false)
    workspace.vm.$emit('update:modelValue', 'f(x)=ax+b\ntexte de la photo')
    await new Promise((resolve) => setTimeout(resolve, 1600))
    expect(api.saveNotes).toHaveBeenLastCalledWith(1, 'f(x)=ax+b\ntexte de la photo', 'mixed', {
      keepalive: false,
      checkpoint: 'photo',
    })

    workspace.vm.$emit('update:modelValue', 'f(x)=ax+b\ntexte corrigé')
    await new Promise((resolve) => setTimeout(resolve, 1600))
    expect(api.saveNotes).toHaveBeenLastCalledWith(1, 'f(x)=ax+b\ntexte corrigé', 'mixed', {
      keepalive: false,
      checkpoint: undefined,
    })
  })

  it('remet une ancienne version des notes depuis l’historique', async () => {
    api.noteVersions.mockResolvedValue([
      {
        id: 7,
        reason: 'photo',
        source: 'photo',
        created_at: '2026-10-03T20:00:00Z',
        words: 3,
        preview: 'ancienne version',
      },
    ])
    api.noteVersion.mockResolvedValue({
      id: 7,
      reason: 'photo',
      source: 'photo',
      created_at: '2026-10-03T20:00:00Z',
      words: 3,
      preview: 'ancienne version',
      raw_text: 'ancienne version',
    })
    api.restoreNoteVersion.mockResolvedValue({ raw_text: 'ancienne version', source: 'photo' })
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const { wrapper } = await mountChapter()

    await wrapper.find('.history-toggle').trigger('click')
    await flushPromises()
    expect(wrapper.find('.notes-history').text()).toContain('Juste après l’import d’une photo')
    await wrapper.find('.notes-history .version-list button').trigger('click')
    await flushPromises()
    expect(wrapper.find('.notes-version-text').text()).toBe('ancienne version')
    const restore = wrapper
      .findAll('.notes-history button')
      .find((b) => b.text().includes('Remettre cette version'))!
    await restore.trigger('click')
    await flushPromises()

    expect(api.restoreNoteVersion).toHaveBeenCalledWith(1, 7)
    expect(wrapper.find('.notes-history').exists()).toBe(false)
    expect((wrapper.find('.notes-stub').element as HTMLTextAreaElement).value).toBe(
      'ancienne version',
    )
  })

  it('renomme le chapitre depuis le menu', async () => {
    api.renameChapter.mockImplementation(async (_id: number, title: string) => ({
      ...(await api.chapter()),
      title,
    }))
    const { wrapper } = await mountChapter()

    await wrapper.find('[aria-label="Plus d\'actions"]').trigger('click')
    await wrapper.findAll('.menu-panel button')[0]!.trigger('click')
    await wrapper.find('#rename').setValue('Les fonctions affines')
    await wrapper.find('.rename-form').trigger('submit')
    await flushPromises()

    expect(api.renameChapter).toHaveBeenCalledWith(1, 'Les fonctions affines')
    expect(wrapper.find('h1').text()).toBe('Les fonctions affines')
  })

  it('supprime le chapitre après confirmation et revient à la matière', async () => {
    api.deleteChapter.mockResolvedValue(undefined)
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true)
    const { wrapper, router } = await mountChapter()

    await wrapper.find('[aria-label="Plus d\'actions"]').trigger('click')
    await wrapper.find('.danger-item').trigger('click')
    await flushPromises()

    expect(confirm).toHaveBeenCalledWith(expect.stringContaining('corbeille'))
    expect(api.deleteChapter).toHaveBeenCalledWith(1)
    expect(api.saveNotes).not.toHaveBeenCalled()
    expect(router.currentRoute.value.fullPath).toBe('/matieres/mathematiques')
    confirm.mockRestore()
  })

  it('propose le titre trouvé par la mise au propre', async () => {
    api.chapter.mockResolvedValue({
      id: 1,
      title: 'je sais pas',
      subject_id: 2,
      subject: { id: 2, name: 'Physique-Chimie', slug: 'physique-chimie' },
      progress: null,
    })
    api.course.mockResolvedValue(course({ title: 'Espèces chimiques et mélanges' }))
    api.renameChapter.mockResolvedValue({
      ...(await api.chapter()),
      title: 'Espèces chimiques et mélanges',
    })
    const { wrapper } = await mountChapter()

    expect(wrapper.find('.title-proposal').text()).toContain('Espèces chimiques et mélanges')
    await wrapper.find('.title-proposal button.secondary').trigger('click')
    await flushPromises()

    expect(api.renameChapter).toHaveBeenCalledWith(1, 'Espèces chimiques et mélanges')
    expect(wrapper.find('h1').text()).toBe('Espèces chimiques et mélanges')
    expect(wrapper.find('.title-proposal').exists()).toBe(false)
  })

  it('ne propose pas un titre identique ou illisible', async () => {
    api.course.mockResolvedValue(course({ title: 'Fonctions Affines !' }))
    let { wrapper } = await mountChapter()
    expect(wrapper.find('.title-proposal').exists()).toBe(false)

    api.course.mockResolvedValue(course({ title: 'Chimie [illisible]' }))
    ;({ wrapper } = await mountChapter())
    expect(wrapper.find('.title-proposal').exists()).toBe(false)
  })
})
