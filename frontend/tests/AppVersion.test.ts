import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import AppVersion from '../src/components/AppVersion.vue'

const api = vi.hoisted(() => ({ appVersion: vi.fn() }))
vi.mock('../src/api/client', () => ({ api }))

describe('AppVersion', () => {
  it('affiche la version de l’application', async () => {
    api.appVersion.mockResolvedValue({ version: '0.1.0-beta.2' })
    const wrapper = mount(AppVersion)
    await flushPromises()
    expect(wrapper.text()).toBe('NoteClaire, version 0.1.0-beta.2')
  })

  it('n’affiche rien si le serveur ne répond pas', async () => {
    api.appVersion.mockRejectedValue(new Error('hors ligne'))
    const wrapper = mount(AppVersion)
    await flushPromises()
    expect(wrapper.text()).toBe('')
  })
})
