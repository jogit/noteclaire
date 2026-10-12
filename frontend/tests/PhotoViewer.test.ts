import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import PhotoViewer from '../src/components/PhotoViewer.vue'

const photos = [{ url: '/api/photos/3/a.jpg', name: 'page 1' }]

function mountViewer() {
  return mount(PhotoViewer, { props: { photos }, attachTo: document.body })
}

const transform = (wrapper: ReturnType<typeof mount>) =>
  wrapper.find('.photo-stage').attributes('style') ?? ''

function pointer(type: string, x: number, y: number, id = 1) {
  return new PointerEvent(type, { clientX: x, clientY: y, pointerId: id, bubbles: true })
}

describe('PhotoViewer', () => {
  afterEach(() => vi.restoreAllMocks())

  it('zoome avec la molette et revient à la taille normale', async () => {
    const wrapper = mountViewer()
    expect(transform(wrapper)).toContain('scale(1)')

    await wrapper.find('.photo-frame').trigger('wheel', { deltaY: -300 })
    expect(transform(wrapper)).not.toContain('scale(1)')

    await wrapper
      .findAll('button')
      .find((b) => b.text().includes('Taille normale'))!
      .trigger('click')
    expect(transform(wrapper)).toContain('scale(1)')
    wrapper.unmount()
  })

  it('zoome avec les boutons et au clavier, sans jamais passer sous la taille normale', async () => {
    const wrapper = mountViewer()
    await wrapper.find('button[aria-label="Zoom avant"]').trigger('click')
    expect(transform(wrapper)).toContain('scale(1.4)')
    await wrapper.find('.photo-frame').trigger('keydown', { key: '0' })
    expect(transform(wrapper)).toContain('scale(1)')
    await wrapper.find('button[aria-label="Zoom arrière"]').trigger('click')
    expect(transform(wrapper)).toContain('scale(1)')
    wrapper.unmount()
  })

  it('agrandit au double-clic et revient au second', async () => {
    const wrapper = mountViewer()
    await wrapper.find('.photo-frame').trigger('dblclick', { clientX: 10, clientY: 10 })
    expect(transform(wrapper)).toContain('scale(2.5)')
    await wrapper.find('.photo-frame').trigger('dblclick')
    expect(transform(wrapper)).toContain('scale(1)')
    wrapper.unmount()
  })

  it('déplace la photo zoomée en glissant, sans la sortir du cadre', async () => {
    vi.spyOn(HTMLElement.prototype, 'clientWidth', 'get').mockReturnValue(400)
    vi.spyOn(HTMLElement.prototype, 'clientHeight', 'get').mockReturnValue(300)
    const wrapper = mountViewer()
    const frame = wrapper.find('.photo-frame').element
    await wrapper.find('button[aria-label="Zoom avant"]').trigger('click') // 1.4 : marge de 160 px
    const start = transform(wrapper)

    frame.dispatchEvent(pointer('pointerdown', 200, 150))
    frame.dispatchEvent(pointer('pointermove', 150, 150))
    await wrapper.vm.$nextTick()
    expect(transform(wrapper)).not.toBe(start)
    frame.dispatchEvent(pointer('pointermove', -3000, 150)) // très loin : reste dans la photo
    frame.dispatchEvent(pointer('pointerup', -3000, 150))
    await wrapper.vm.$nextTick()
    expect(transform(wrapper)).toContain('translate(-160px')
    wrapper.unmount()
  })
})
