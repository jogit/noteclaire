import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../src/api/errors'
import NotesWorkspace from '../src/components/NotesWorkspace.vue'

const api = vi.hoisted(() => ({
  photo: vi.fn(),
  photos: vi.fn(),
  uploadImage: vi.fn(),
}))
vi.mock('../src/api/client', () => ({ api }))

function choose(wrapper: ReturnType<typeof mount>, selector: string, files: File[]) {
  const input = wrapper.find(selector)
  Object.defineProperty(input.element, 'files', { value: files, configurable: true })
  return input.trigger('change')
}

async function mountWorkspace(notes = '') {
  const wrapper = mount(NotesWorkspace, {
    props: {
      chapterId: 3,
      modelValue: notes,
      'onUpdate:modelValue': (value: string) => wrapper.setProps({ modelValue: value }),
    },
    attachTo: document.body,
  })
  await flushPromises()
  return wrapper
}

describe('NotesWorkspace', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.photos.mockResolvedValue([])
    URL.createObjectURL = vi.fn(() => 'blob:photo')
    URL.revokeObjectURL = vi.fn()
  })

  it('insère le texte lu sur la photo, la montre à côté et compte les passages à vérifier', async () => {
    api.photo.mockResolvedValue({
      text: 'les plantes [?] la lumière\n[?] rophylle',
      uncertain: [
        { guess: 'vertes captent', options: ['vertes utilisent'] },
        { guess: '', options: [] },
      ],
      url: '/api/photos/3/abc.jpg',
    })
    const wrapper = await mountWorkspace()

    await choose(wrapper, 'input[id^="notes-photo"]', [new File(['x'], 'page.jpg')])
    await flushPromises()

    expect(wrapper.props('modelValue')).toBe(
      'les plantes [?vertes captent|vertes utilisent] la lumière\n[illisible] rophylle',
    )
    expect(wrapper.emitted('captured')).toEqual([[true]])
    expect(wrapper.find('.photo-viewer img').attributes('src')).toBe('blob:photo')
    expect(wrapper.find('.review-bar').text()).toContain('2 passages à vérifier')
    wrapper.unmount()
  })

  it('ajoute un schéma découpé dans la photo', async () => {
    api.photo.mockResolvedValue({ text: 'texte', uncertain: [] })
    api.uploadImage.mockResolvedValue({ url: '/api/images/3/s.jpg' })
    const wrapper = await mountWorkspace('notes')
    await choose(wrapper, 'input[id^="notes-photo"]', [new File(['x'], 'page.jpg')])
    await flushPromises()

    wrapper.findComponent({ name: 'PhotoViewer' }).vm.$emit('crop', new Blob(['img']))
    await flushPromises()

    expect(api.uploadImage).toHaveBeenCalledWith(3, expect.any(File))
    expect(wrapper.props('modelValue')).toContain('![Schéma](/api/images/3/s.jpg)')
    wrapper.unmount()
  })

  it('ajoute une image depuis le bouton dédié', async () => {
    api.uploadImage.mockResolvedValue({ url: '/api/images/3/i.jpg' })
    const wrapper = await mountWorkspace('notes')
    await choose(wrapper, 'input[id^="notes-image"]', [new File(['x'], 'schema.jpg')])
    await flushPromises()
    expect(wrapper.props('modelValue')).toContain('![Schéma](/api/images/3/i.jpg)')
    wrapper.unmount()
  })
})

describe("NotesWorkspace — photos d'origine", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    URL.revokeObjectURL = vi.fn()
  })

  it('propose de revoir les photos conservées du chapitre', async () => {
    api.photos.mockResolvedValue([
      { url: '/api/photos/3/a.jpg', created_at: '2026-10-01T10:00:00Z' },
      { url: '/api/photos/3/b.jpg', created_at: '2026-10-02T10:00:00Z' },
    ])
    const wrapper = await mountWorkspace()

    const button = wrapper.findAll('button').find((b) => b.text().includes("Photos d'origine"))
    expect(button?.text()).toContain('(2)')
    await button!.trigger('click')

    expect(wrapper.find('img[src="/api/photos/3/a.jpg"]').exists()).toBe(true)
  })

  it("n'affiche pas le bouton quand aucune photo n'a été importée", async () => {
    api.photos.mockResolvedValue([])
    const wrapper = await mountWorkspace()
    expect(wrapper.text()).not.toContain("Photos d'origine")
  })

  describe('leçon sur plusieurs pages', () => {
    const page = (name: string) => new File(['x'], name)
    const reading = (text: string) => ({ text, uncertain: [] })

    it('ajoute chaque page à la suite des notes, dans l’ordre choisi', async () => {
      api.photo
        .mockResolvedValueOnce(reading('page un'))
        .mockResolvedValueOnce(reading('page deux'))
        .mockResolvedValueOnce(reading('page trois'))
      const wrapper = await mountWorkspace()

      await choose(wrapper, 'input[id^="notes-photo"]', [
        page('1.jpg'),
        page('2.jpg'),
        page('3.jpg'),
      ])
      await flushPromises()

      expect(api.photo.mock.calls.map(([, file]) => file.name)).toEqual(['1.jpg', '2.jpg', '3.jpg'])
      const notes = wrapper.props('modelValue') as string
      expect(notes.indexOf('page un')).toBeLessThan(notes.indexOf('page deux'))
      expect(notes.indexOf('page deux')).toBeLessThan(notes.indexOf('page trois'))
      expect(wrapper.find('.message.success').text()).toContain('3 photos lues et ajoutées')
      wrapper.unmount()
    })

    it('continue après une photo illisible et propose de la réessayer seule', async () => {
      api.photo
        .mockResolvedValueOnce(reading('page un'))
        .mockRejectedValueOnce(new ApiError('photo_no_text', 422, 'Aucun texte lisible.'))
        .mockResolvedValueOnce(reading('page trois'))
      const wrapper = await mountWorkspace()

      await choose(wrapper, 'input[id^="notes-photo"]', [
        page('1.jpg'),
        page('2.jpg'),
        page('3.jpg'),
      ])
      await flushPromises()

      expect(wrapper.props('modelValue')).toContain('page trois')
      expect(wrapper.find('.message.success').text()).toContain('2 photos lues')
      const warning = wrapper.find('.message.warning')
      expect(warning.text()).toContain('Une photo n’a pas été lue')
      expect(warning.text()).toContain('2.jpg')

      api.photo.mockResolvedValueOnce(reading('page deux'))
      await warning.find('button').trigger('click')
      await flushPromises()
      expect(api.photo).toHaveBeenCalledTimes(4)
      expect(api.photo.mock.calls[3][1].name).toBe('2.jpg')
      expect(wrapper.find('.message.warning').exists()).toBe(false)
      wrapper.unmount()
    })

    it('s’arrête quand l’IA est indisponible et garde les autres pages à réessayer', async () => {
      api.photo
        .mockResolvedValueOnce(reading('page un'))
        .mockRejectedValueOnce(new ApiError('ai_unavailable', 503, 'IA indisponible'))
      const wrapper = await mountWorkspace()

      await choose(wrapper, 'input[id^="notes-photo"]', [
        page('1.jpg'),
        page('2.jpg'),
        page('3.jpg'),
      ])
      await flushPromises()

      expect(api.photo).toHaveBeenCalledTimes(2) // la 3e n'est pas envoyée
      const items = wrapper.findAll('.message.warning li').map((li) => li.text())
      expect(items).toHaveLength(2)
      expect(items[0]).toContain('2.jpg')
      expect(items[1]).toContain('3.jpg')
      expect(wrapper.find('.message.warning').text()).toContain('2 photos n’ont pas été lues')
      wrapper.unmount()
    })

    it('rappelle qu’on peut ajouter les pages au fur et à mesure', async () => {
      const wrapper = await mountWorkspace()
      expect(wrapper.find('.hint').text()).toContain('plusieurs pages')
      wrapper.unmount()
    })
  })

  it('remplace les [schéma : …] par les schémas découpés automatiquement', async () => {
    api.photo.mockResolvedValue({
      text: 'avant\n[schéma : flèches annotées]\nmilieu\n[schéma : un cycle]\naprès',
      uncertain: [],
      figures: [{ index: 1, url: '/api/images/3/' + 'c'.repeat(32) + '.jpg' }],
    })
    const wrapper = await mountWorkspace()
    await choose(wrapper, 'input[id^="notes-photo"]', [new File(['x'], 'page.jpg')])
    await flushPromises()

    const notes = wrapper.props('modelValue') as string
    expect(notes).toContain('[schéma : flèches annotées]') // pas découpé : le repère reste
    expect(notes).toContain('![un cycle](/api/images/3/' + 'c'.repeat(32) + '.jpg)')
    expect(notes).not.toContain('[schéma : un cycle]')
    wrapper.unmount()
  })

  it('remplace une photo par son schéma redessiné dans les notes', async () => {
    const photo = '/api/images/3/' + 'a'.repeat(32) + '.jpg'
    const clean = '/api/images/3/' + 'b'.repeat(32) + '.svg'
    const wrapper = await mountWorkspace(`avant\n![schéma](${photo})\naprès`)
    wrapper.findComponent({ name: 'SchemaList' }).vm.$emit('replace', photo, clean)
    await flushPromises()
    expect(wrapper.props('modelValue')).toBe(`avant\n![schéma](${clean})\naprès`)
    wrapper.unmount()
  })

  describe('prendre une photo', () => {
    const takeButton = (wrapper: ReturnType<typeof mount>) =>
      wrapper.findAll('button').find((b) => b.text().includes('Prendre une photo'))!

    it('ouvre la caméra du navigateur quand elle est disponible', async () => {
      const getUserMedia = vi.fn().mockResolvedValue({ getTracks: () => [] })
      Object.defineProperty(navigator, 'mediaDevices', {
        value: { getUserMedia },
        configurable: true,
      })
      const wrapper = await mountWorkspace()
      await takeButton(wrapper).trigger('click')
      await flushPromises()
      expect(getUserMedia).toHaveBeenCalled()
      wrapper.unmount()
    })

    it('lit la photo reçue de la caméra comme une photo de notes', async () => {
      api.photo.mockResolvedValue({ text: 'cours', uncertain: [] })
      const wrapper = await mountWorkspace()
      const file = new File(['x'], 'photo-camera.jpg')
      wrapper.findComponent({ name: 'CameraDialog' }).vm.$emit('photo', file)
      await flushPromises()
      expect(api.photo).toHaveBeenCalledWith(3, file)
      expect(wrapper.props('modelValue')).toContain('cours')
      wrapper.unmount()
    })

    it('se rabat sur l’appareil photo du téléphone sans caméra navigateur', async () => {
      Object.defineProperty(navigator, 'mediaDevices', { value: undefined, configurable: true })
      const wrapper = await mountWorkspace()
      const click = vi.spyOn(wrapper.find('input[capture]').element as HTMLInputElement, 'click')
      await takeButton(wrapper).trigger('click')
      expect(click).toHaveBeenCalled()
      wrapper.unmount()
    })
  })
})
