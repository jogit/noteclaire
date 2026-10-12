import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import RichCourseEditor from '../src/components/RichCourseEditor.vue'

const api = vi.hoisted(() => ({ uploadImage: vi.fn() }))
vi.mock('../src/api/client', () => ({ api }))

async function mountEditor(content: string) {
  const wrapper = mount(RichCourseEditor, {
    props: { chapterId: 1, content, saving: false },
    attachTo: document.body,
  })
  await flushPromises()
  return wrapper
}

const button = (wrapper: Awaited<ReturnType<typeof mountEditor>>, text: string) =>
  wrapper.findAll('button').find((b) => b.text().trim() === text)!

describe('RichCourseEditor', () => {
  it('affiche le cours mis en forme, sans Markdown visible', async () => {
    const wrapper = await mountEditor('# Titre\n\n::: definition Vecteur\nUn ==vecteur==.\n:::')
    expect(wrapper.find('.rich-editor-content h1').text()).toBe('Titre')
    expect(wrapper.find('.rich-editor-content aside.callout-definition').exists()).toBe(true)
    expect(wrapper.find('.rich-editor-content mark').text()).toBe('vecteur')
    expect(wrapper.text()).not.toContain(':::')
    wrapper.unmount()
  })

  it('met un paragraphe en encadré et enregistre du Markdown', async () => {
    const wrapper = await mountEditor('Une espèce chimique est un ensemble.')
    expect(button(wrapper, 'Enregistrer').attributes('disabled')).toBeDefined()

    await button(wrapper, 'Définition').trigger('click')
    await button(wrapper, 'Enregistrer').trigger('click')

    expect(wrapper.emitted('save')).toEqual([
      ['::: definition\nUne espèce chimique est un ensemble.\n:::'],
    ])
    wrapper.unmount()
  })

  it('propose le mode avancé', async () => {
    const wrapper = await mountEditor('Texte')
    await wrapper.find('.advanced-link').trigger('click')
    expect(wrapper.emitted('advanced')).toHaveLength(1)
    wrapper.unmount()
  })
})
