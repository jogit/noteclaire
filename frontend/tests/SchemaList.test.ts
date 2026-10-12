import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import SchemaList from '../src/components/SchemaList.vue'

const api = vi.hoisted(() => ({
  redrawSchema: vi.fn(),
  restyleSchema: vi.fn(),
  expectedDurations: vi.fn(),
}))
vi.mock('../src/api/client', () => ({ api }))

const PHOTO = '/api/images/3/' + 'a'.repeat(32) + '.jpg'
const CLEAN = '/api/images/3/' + 'b'.repeat(32) + '.svg'
const notes = `Cours\n![flèches annotées](${PHOTO})\n![déjà propre](${CLEAN})\nfin`

function mountList(text = notes) {
  return mount(SchemaList, { props: { chapterId: 3, notes: text } })
}

describe('SchemaList', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.expectedDurations?.mockResolvedValue({})
  })

  it('liste seulement les schémas photographiés, pas ceux déjà redessinés', () => {
    const wrapper = mountList()
    const items = wrapper.findAll('li')
    expect(items).toHaveLength(1)
    expect(items[0]!.find('img').attributes('src')).toBe(PHOTO)
    expect(items[0]!.text()).toContain('flèches annotées')
  })

  it('n’affiche rien quand les notes n’ont aucun schéma', () => {
    expect(mountList('juste du texte').find('section').exists()).toBe(false)
  })

  it('propose l’avant/après et ne remplace que sur accord', async () => {
    api.redrawSchema.mockResolvedValue({ url: CLEAN, corrections: [] })
    const wrapper = mountList()
    await wrapper.find('li button.secondary').trigger('click')
    await flushPromises()

    expect(api.redrawSchema).toHaveBeenCalledWith(3, PHOTO, undefined)
    const compare = wrapper.find('.schema-compare')
    expect(compare.findAll('img').map((i) => i.attributes('src'))).toEqual([PHOTO, CLEAN])
    expect(wrapper.emitted('replace')).toBeUndefined() // rien ne change sans l'accord de l'élève

    await compare.find('button.primary').trigger('click')
    expect(wrapper.emitted('replace')).toEqual([[PHOTO, CLEAN]])
    expect(wrapper.find('.schema-compare').exists()).toBe(false)
  })

  it('garde la photo quand l’élève refuse', async () => {
    api.redrawSchema.mockResolvedValue({ url: CLEAN, corrections: [] })
    const wrapper = mountList()
    await wrapper.find('li button.secondary').trigger('click')
    await flushPromises()
    await wrapper.find('.schema-compare button.ghost').trigger('click')
    expect(wrapper.emitted('replace')).toBeUndefined()
    expect(wrapper.find('.schema-compare').exists()).toBe(false)
  })

  it('affiche l’erreur sans rien perdre', async () => {
    api.redrawSchema.mockRejectedValue(new Error('boom'))
    const wrapper = mountList()
    await wrapper.find('li button.secondary').trigger('click')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').exists()).toBe(true)
    expect(wrapper.find('li button.secondary').attributes('disabled')).toBeUndefined()
  })

  it('corrige la version proposée avec la remarque de l’élève', async () => {
    const better = '/api/images/3/' + 'c'.repeat(32) + '.svg'
    api.redrawSchema
      .mockResolvedValueOnce({ url: CLEAN, corrections: [] })
      .mockResolvedValueOnce({ url: better, corrections: [] })
    const wrapper = mountList()
    await wrapper.find('li button.secondary').trigger('click')
    await flushPromises()

    const button = wrapper.find('.schema-remark button')
    expect(button.attributes('disabled')).toBeDefined() // pas de remarque : rien à envoyer
    await wrapper.find('.schema-remark input').setValue('  il manque une pointe  ')
    await wrapper.find('.schema-remark').trigger('submit')
    await flushPromises()

    expect(api.redrawSchema).toHaveBeenLastCalledWith(3, PHOTO, {
      previousUrl: CLEAN,
      remark: 'il manque une pointe',
    })
    const images = wrapper.find('.schema-compare').findAll('img')
    expect(images.map((i) => i.attributes('src'))).toEqual([PHOTO, better])
    expect((wrapper.find('.schema-remark input').element as HTMLInputElement).value).toBe('')

    await wrapper.find('.schema-compare button.primary').trigger('click')
    expect(wrapper.emitted('replace')).toEqual([[PHOTO, better]])
  })

  it('passe la version proposée à l’aspect manuscrit sans la redemander à l’IA', async () => {
    const hand = '/api/images/3/' + 'd'.repeat(32) + '.svg'
    api.redrawSchema.mockResolvedValue({ url: CLEAN, corrections: [] })
    api.restyleSchema.mockResolvedValue({ url: hand })
    const wrapper = mountList()
    await wrapper.find('li button.secondary').trigger('click')
    await flushPromises()

    await wrapper.find('.hand-option input').setValue(true)
    await flushPromises()

    expect(api.restyleSchema).toHaveBeenCalledWith(3, CLEAN, true)
    expect(api.redrawSchema).toHaveBeenCalledTimes(1)
    const images = wrapper.find('.schema-compare').findAll('img')
    expect(images.map((i) => i.attributes('src'))).toEqual([PHOTO, hand])
  })

  it('explique à l’élève ce que l’IA a corrigé dans son schéma', async () => {
    const note = 'Tu avais écrit ⇉ ; j’ai mis ⇌ : c’est un équilibre.'
    api.redrawSchema.mockResolvedValue({ url: CLEAN, corrections: [note] })
    const wrapper = mountList()
    await wrapper.find('li button.secondary').trigger('click')
    await flushPromises()
    expect(wrapper.find('.corrections').text()).toContain(note)
  })
})
