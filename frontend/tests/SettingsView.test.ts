import { shallowMount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import SettingsView from '../src/views/SettingsView.vue'

const route = vi.hoisted(() => ({ query: {} as Record<string, string> }))
const replace = vi.hoisted(() => vi.fn())
vi.mock('vue-router', () => ({ useRoute: () => route, useRouter: () => ({ replace }) }))

const tab = (wrapper: ReturnType<typeof shallowMount>, label: string) =>
  wrapper.findAll('[role="tab"]').find((t) => t.text() === label)!

describe('SettingsView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    route.query = {}
  })

  it('ouvre les élèves par défaut et change de rubrique en gardant l’onglet dans l’adresse', async () => {
    const wrapper = shallowMount(SettingsView)
    expect(tab(wrapper, 'Élèves').attributes('aria-selected')).toBe('true')
    expect(wrapper.findComponent({ name: 'StudentsSection' }).exists()).toBe(true)

    await tab(wrapper, 'Sauvegardes').trigger('click')
    expect(replace).toHaveBeenCalledWith({ query: { onglet: 'sauvegardes' } })
    expect(wrapper.findComponent({ name: 'BackupSection' }).exists()).toBe(true)
    expect(wrapper.findComponent({ name: 'StudentsSection' }).exists()).toBe(false)
  })

  it('retrouve l’onglet demandé dans l’adresse', () => {
    route.query = { onglet: 'avance' }
    const wrapper = shallowMount(SettingsView)
    expect(wrapper.findComponent({ name: 'SubjectsSection' }).exists()).toBe(true)
  })

  it('ignore un onglet inconnu', () => {
    route.query = { onglet: 'nimporte-quoi' }
    const wrapper = shallowMount(SettingsView)
    expect(tab(wrapper, 'Élèves').attributes('aria-selected')).toBe('true')
  })

  it('ouvre l’IA au retour de la connexion ChatGPT', () => {
    route.query = { chatgpt: 'connecte' }
    const wrapper = shallowMount(SettingsView)
    expect(tab(wrapper, 'Intelligence artificielle').attributes('aria-selected')).toBe('true')
    expect(wrapper.findComponent({ name: 'ChatGptSection' }).exists()).toBe(true)
  })
})
