import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import NotesEditor from '../src/components/NotesEditor.vue'

type Exposed = {
  insertInline: (text: string) => void
  insertBlock: (notes: string) => void
  insertImage: (src: string, alt: string) => void
  nextSpot: () => void
  contextBeforeCursor: () => string
  spots: { pos: number }[]
}

async function mountEditor(notes: string) {
  const wrapper = mount(NotesEditor, { props: { modelValue: notes }, attachTo: document.body })
  await flushPromises()
  return { wrapper, editor: wrapper.vm as unknown as Exposed }
}

const lastNotes = (wrapper: Awaited<ReturnType<typeof mountEditor>>['wrapper']) =>
  wrapper.emitted('update:modelValue')!.at(-1)![0]

describe('NotesEditor', () => {
  it('affiche les passages incertains comme des étiquettes, sans repères techniques', async () => {
    const { wrapper, editor } = await mountEditor('la [?cellule|celule] est [illisible]')
    const spots = wrapper.findAll('.spot')
    expect(spots.map((s) => s.text())).toEqual(['cellule', 'illisible'])
    expect(spots[0]!.classes()).toContain('spot-doubt')
    expect(spots[1]!.classes()).toContain('spot-illegible')
    expect(wrapper.text()).not.toContain('[?')
    expect(editor.spots).toHaveLength(2)
    wrapper.unmount()
  })

  it('remplace un passage par la proposition choisie', async () => {
    const { wrapper, editor } = await mountEditor('la [?cellule|celule] du vivant')
    await wrapper.find('.spot').trigger('click')
    const choices = wrapper.findAll('.spot-choices button').map((b) => b.text())
    expect(choices).toEqual(['cellule', 'celule'])

    await wrapper.findAll('.spot-choices button')[0]!.trigger('click')

    expect(lastNotes(wrapper)).toBe('la cellule du vivant')
    expect(editor.spots).toHaveLength(0)
    expect(wrapper.find('.spot-popover').exists()).toBe(false)
    wrapper.unmount()
  })

  it('accepte ce que l’élève lit dans son cahier, ou laisse illisible', async () => {
    const { wrapper } = await mountEditor('A [illisible] B [?chlo|clo]')
    await wrapper.findAll('.spot')[0]!.trigger('click')
    await wrapper.find('#spot-custom').setValue('noyau')
    await wrapper.find('.spot-custom').trigger('submit')
    expect(lastNotes(wrapper)).toBe('A noyau B [?chlo|clo]')

    await wrapper.find('.spot').trigger('click')
    await wrapper.findAll('.spot-actions button')[0]!.trigger('click') // Je ne sais pas
    expect(lastNotes(wrapper)).toBe('A noyau B [illisible]')
    wrapper.unmount()
  })

  it('passe au passage suivant à vérifier', async () => {
    const { wrapper, editor } = await mountEditor('a [?b|c] d [?e|f]')
    editor.nextSpot()
    await flushPromises()
    expect(wrapper.find('.spot-popover').exists()).toBe(true)
    expect(wrapper.find('.spot-choices button').text()).toBe('b')
    wrapper.unmount()
  })

  it('insère le texte d’une photo en bloc, puis une image', async () => {
    const { wrapper, editor } = await mountEditor('Chapitre')
    editor.insertBlock('ligne 1\nla [?norme|forme]')
    expect(lastNotes(wrapper)).toBe('Chapitre\nligne 1\nla [?norme|forme]')

    editor.insertImage('/api/images/1/a.jpg', 'Schéma')
    expect(lastNotes(wrapper)).toContain('![Schéma](/api/images/1/a.jpg)')
    // Ces insertions ne comptent pas comme de la frappe au clavier.
    expect(wrapper.emitted('typed')).toBeUndefined()
    wrapper.unmount()
  })
})
