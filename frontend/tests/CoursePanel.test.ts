import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Course } from '../src/api/types'
import CoursePanel from '../src/components/CoursePanel.vue'
import { suggestion } from './fixtures'

const api = vi.hoisted(() => ({
  updateCourse: vi.fn(),
  versions: vi.fn(),
  version: vi.fn(),
  explain: vi.fn(),
  pendingSuggestions: vi.fn(),
  references: vi.fn(),
  analyze: vi.fn(),
  acceptSuggestion: vi.fn(),
}))
vi.mock('../src/api/client', () => ({ api }))

const course: Course = {
  chapter_id: 1,
  content_markdown: '# Cours\n\nTexte',
  version: 2,
  origin: 'ai_structure',
  created_at: '2026-10-03T20:00:00Z',
  notes_changed: false,
  has_manual_changes: false,
  title: 'Cours',
}

function mountPanel(props: Partial<{ notes: string; course: Course }> = {}) {
  return mount(CoursePanel, {
    props: { chapterId: 1, subjectId: 2, notes: 'Texte', course, ...props },
    global: { stubs: { RouterLink: true } },
    attachTo: document.body,
  })
}

const button = (wrapper: ReturnType<typeof mountPanel>, text: string) =>
  wrapper.findAll('button').find((b) => b.text().includes(text))!

describe('CoursePanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    document.body.innerHTML = ''
    localStorage.clear()
    api.pendingSuggestions.mockResolvedValue([])
    api.references.mockResolvedValue([])
  })

  it('enregistre une modification manuelle comme nouvelle version', async () => {
    const edited = { ...course, version: 3, origin: 'user_edit', content_markdown: '# Modifié' }
    api.updateCourse.mockResolvedValue(edited)
    const wrapper = mountPanel()

    await button(wrapper, 'Modifier').trigger('click')
    // L'éditeur visuel est chargé à la demande.
    await vi.waitFor(() => expect(button(wrapper, 'Mode avancé')).toBeTruthy())
    await button(wrapper, 'Mode avancé').trigger('click')
    await wrapper.find('#course-markdown').setValue('# Modifié')
    expect(wrapper.find('.preview h1').text()).toBe('Modifié')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(api.updateCourse).toHaveBeenCalledWith(1, '# Modifié')
    expect(wrapper.emitted('update:course')).toEqual([[edited]])
  })

  it('passe du Markdown à l’éditeur visuel et retour sans perdre la modification', async () => {
    const wrapper = mountPanel()
    await button(wrapper, 'Modifier').trigger('click')
    await vi.waitFor(() => expect(button(wrapper, 'Mode avancé')).toBeTruthy())
    await button(wrapper, 'Mode avancé').trigger('click')
    await wrapper.find('#course-markdown').setValue('# Cours\n\nTexte modifié')

    await button(wrapper, "Revenir à l'éditeur visuel").trigger('click')
    await vi.waitFor(() => expect(wrapper.find('.rich-editor-content').exists()).toBe(true))
    await vi.waitFor(() =>
      expect(wrapper.find('.rich-editor-content').text()).toContain('Texte modifié'),
    )
    expect(button(wrapper, 'Enregistrer').attributes('disabled')).toBeUndefined()
    expect(localStorage.getItem('noteclaire.courseEditor')).toBe('visual')

    await button(wrapper, 'Mode avancé').trigger('click')
    expect((wrapper.find('#course-markdown').element as HTMLTextAreaElement).value).toContain(
      'Texte modifié',
    )
    expect(localStorage.getItem('noteclaire.courseEditor')).toBe('markdown')
  })

  it('ferme le bandeau de sélection : croix, Échap ou clic ailleurs', async () => {
    const wrapper = mountPanel()
    const select = async () => {
      const range = document.createRange()
      range.selectNodeContents(wrapper.find('.markdown p').element)
      document.getSelection()!.removeAllRanges()
      document.getSelection()!.addRange(range)
      document.dispatchEvent(new Event('selectionchange'))
      await flushPromises()
    }
    const deselect = async (target: Element) => {
      target.dispatchEvent(new Event('pointerdown', { bubbles: true }))
      document.getSelection()!.removeAllRanges()
      document.dispatchEvent(new Event('selectionchange'))
      await flushPromises()
    }

    await select()
    await wrapper.find('.selection-bar [aria-label="Fermer"]').trigger('click')
    expect(wrapper.find('.selection-bar').exists()).toBe(false)

    await select()
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await flushPromises()
    expect(wrapper.find('.selection-bar').exists()).toBe(false)

    await select()
    await deselect(wrapper.find('.markdown h1').element)
    expect(wrapper.find('.selection-bar').exists()).toBe(false)

    // Un clic dans le bandeau annule aussi la sélection, mais le bandeau reste.
    await select()
    await deselect(wrapper.find('.selection-bar').element)
    expect(wrapper.find('.selection-bar').exists()).toBe(true)
  })

  it('affiche les modifications par rapport aux notes', async () => {
    const wrapper = mountPanel({
      notes: 'la fonction é affine',
      course: { ...course, content_markdown: '# Cours\n\nla fonction est affine' },
    })
    await button(wrapper, "Ce que l'IA a changé").trigger('click')
    expect(wrapper.find('.change-list del').text()).toBe('é')
    expect(wrapper.find('.change-list ins').text()).toBe('est')
    expect(wrapper.find('.change-counts').text()).toContain('1 correction')
  })

  it('restaure une ancienne version en créant une nouvelle version', async () => {
    api.versions.mockResolvedValue([
      { version: 2, origin: 'ai_structure', created_at: course.created_at },
      { version: 1, origin: 'user_edit', created_at: course.created_at },
    ])
    api.version.mockResolvedValue({
      version: 1,
      origin: 'user_edit',
      created_at: course.created_at,
      content_markdown: '# Ancien',
    })
    api.updateCourse.mockResolvedValue({ ...course, version: 3 })
    const wrapper = mountPanel()

    await button(wrapper, 'Versions').trigger('click')
    await vi.waitFor(() => expect(button(wrapper, 'Version 1')).toBeTruthy())
    await button(wrapper, 'Version 1').trigger('click')
    await vi.waitFor(() => expect(button(wrapper, 'Restaurer')).toBeTruthy())
    await button(wrapper, 'Restaurer').trigger('click')
    await flushPromises()

    expect(api.updateCourse).toHaveBeenCalledWith(1, '# Ancien')
  })

  it('propose de remettre au propre quand les notes ont changé', async () => {
    const wrapper = mountPanel({ course: { ...course, notes_changed: true } })
    await button(wrapper, 'Remettre le cours au propre').trigger('click')
    expect(wrapper.emitted('restructure')).toHaveLength(1)
  })

  it('avertit quand une partie des notes a disparu du cours', () => {
    const wrapper = mountPanel({
      notes: 'a est le coefficient directeur et b est l’ordonnée à l’origine',
      course: { ...course, content_markdown: '# Fonctions affines' },
    })
    expect(wrapper.text()).toContain('de tes notes ne se retrouvent pas dans le cours')
  })

  it("propose « Je n'ai pas compris » sur le passage sélectionné", async () => {
    const wrapper = mountPanel()
    const range = document.createRange()
    range.selectNodeContents(wrapper.find('.markdown p').element)
    document.getSelection()!.removeAllRanges()
    document.getSelection()!.addRange(range)
    document.dispatchEvent(new Event('selectionchange'))
    await flushPromises()

    expect(wrapper.find('.selection-text').text()).toBe('« Texte »')
    await wrapper.find('.selection-bar button').trigger('click')
    expect(wrapper.find('.explain-quote').text()).toBe('« Texte »')
  })
})

describe('CoursePanel — relecture', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    document.body.innerHTML = ''
    localStorage.clear()
  })

  it('annonce les points sans les montrer, puis les présente un par un', async () => {
    api.pendingSuggestions.mockResolvedValue([
      suggestion(4, { original_text: '**b est la pente**' }),
      suggestion(5, { original_text: 'introuvable dans le cours' }),
    ])
    const wrapper = mountPanel({
      course: { ...course, content_markdown: '# Cours\n\nOn note que **b est la pente** ici.' },
    })
    await flushPromises()
    await flushPromises()

    expect(wrapper.find('.course-review-bar').text()).toContain('2 points à regarder')
    expect(wrapper.emitted('pending')!.at(-1)).toEqual([2])
    // Rien n'est surligné ni affiché tant que l'élève n'a pas choisi de regarder.
    expect(wrapper.find('mark.suggestion-anchor.active').exists()).toBe(false)
    expect(wrapper.find('.review-sheet').exists()).toBe(false)

    await button(wrapper, 'Regarder').trigger('click')
    await flushPromises()
    expect(wrapper.find('.review-sheet h3').text()).toBe('Point 1 sur 2')
    expect(wrapper.findAll('.review-sheet .suggestion')).toHaveLength(1)
    expect(wrapper.find('mark.suggestion-anchor.active').text()).toBe('b est la pente')
    expect(wrapper.find('.review-sheet').text()).toContain('Voir dans le cours')

    await button(wrapper, 'Suivant').trigger('click')
    await flushPromises()
    expect(wrapper.find('.review-sheet h3').text()).toBe('Point 2 sur 2')
    expect(wrapper.find('mark.suggestion-anchor.active').exists()).toBe(false)
    expect(wrapper.find('.review-sheet').text()).not.toContain('Voir dans le cours')

    await wrapper.find('[aria-label="Plus tard"]').trigger('click')
    expect(wrapper.find('.review-sheet').exists()).toBe(false)
  })

  it('applique la suggestion acceptée et termine la relecture', async () => {
    api.pendingSuggestions.mockResolvedValue([suggestion(4, { original_text: 'Texte' })])
    const updated = { ...course, version: 3, content_markdown: '# Cours\n\nTexte corrigé' }
    api.acceptSuggestion.mockResolvedValue({ suggestion: {}, course: updated })
    const wrapper = mountPanel()
    await flushPromises()

    await button(wrapper, 'Regarder').trigger('click')
    await button(wrapper, 'Accepter').trigger('click')
    await flushPromises()
    expect(wrapper.emitted('update:course')).toEqual([[updated]])
    expect(wrapper.emitted('pending')!.at(-1)).toEqual([0])
    expect(wrapper.find('.review-sheet').exists()).toBe(false)
    expect(wrapper.find('.course-review-bar').text()).toContain('Relecture terminée')
  })

  it('demande confirmation avant de remplacer des points non regardés', async () => {
    api.pendingSuggestions.mockResolvedValue([suggestion(4, { original_text: 'Texte' })])
    api.analyze.mockResolvedValue([])
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
    const wrapper = mountPanel()
    await flushPromises()

    await button(wrapper, 'Relire à nouveau').trigger('click')
    expect(confirm.mock.calls[0]![0]).toContain('Il reste 1 point à regarder')
    expect(api.analyze).not.toHaveBeenCalled()

    confirm.mockReturnValue(true)
    await button(wrapper, 'Relire à nouveau').trigger('click')
    await flushPromises()
    expect(api.analyze).toHaveBeenCalledWith(1)
  })

  it('propose de faire relire le cours, puis dit quand tout va bien', async () => {
    api.pendingSuggestions.mockResolvedValue([])
    api.analyze.mockResolvedValue([])
    const wrapper = mountPanel()
    await flushPromises()

    await button(wrapper, "Faire relire mon cours par l'IA").trigger('click')
    await flushPromises()
    expect(api.analyze).toHaveBeenCalledWith(1)
    expect(wrapper.find('.course-review-bar').text()).toContain('Rien à signaler')
  })
})
