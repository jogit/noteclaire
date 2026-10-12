import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import SetupView from '../src/views/SetupView.vue'

const api = vi.hoisted(() => ({
  levels: vi.fn(),
  adaptations: vi.fn(),
  students: vi.fn(),
  updateStudent: vi.fn(),
  setupStatus: vi.fn(),
  saveAI: vi.fn(),
  testAI: vi.fn(),
  chatgptLogin: vi.fn(),
  chatgptStatus: vi.fn(),
  downloadProgrammes: vi.fn(),
}))
vi.mock('../src/api/client', () => ({ api }))
const replace = vi.hoisted(() => vi.fn())
vi.mock('vue-router', () => ({ useRouter: () => ({ replace }) }))

describe('SetupView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.levels.mockResolvedValue([
      { id: 'seconde', name: 'Seconde' },
      { id: 'premiere', name: 'Première' },
    ])
    api.students.mockResolvedValue([
      { id: 1, name: 'Élève', level: 'seconde', adaptation_codes: [], adaptation_notes: '' },
    ])
    api.setupStatus.mockResolvedValue({
      needs_setup: true,
      ai_provider: 'openai',
      has_openai_key: false,
      local_ai_base_url: 'http://host.docker.internal:11434/v1',
      local_ai_model: 'qwen3:8b',
      chatgpt_connected: false,
    })
    api.adaptations.mockResolvedValue([{ id: 'dyslexie', name: 'Dyslexie' }])
    api.updateStudent.mockResolvedValue({})
    api.saveAI.mockResolvedValue({})
    api.testAI.mockResolvedValue({ ok: true, message: 'Connexion réussie.' })
  })

  it('crée le profil, enregistre la clé, teste puis ouvre l’application', async () => {
    const wrapper = mount(SetupView)
    await flushPromises()

    await wrapper.find('#setup-name').setValue('Léa')
    await wrapper.find('#setup-level').setValue('premiere')
    await wrapper.find('input[type="checkbox"]').setValue(true)
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(api.updateStudent).toHaveBeenCalledWith(1, {
      name: 'Léa',
      level: 'premiere',
      adaptation_codes: ['dyslexie'],
      adaptation_notes: '',
    })

    await wrapper.find('#ai-key').setValue('sk-test')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(api.saveAI).toHaveBeenCalledWith(
      expect.objectContaining({ ai_provider: 'openai', openai_api_key: 'sk-test' }),
    )
    expect(wrapper.text()).toContain('Connexion réussie.')

    await wrapper.find('button.primary').trigger('click')
    expect(replace).toHaveBeenCalledWith('/')
  })

  it('lance directement la connexion ChatGPT', async () => {
    api.chatgptLogin.mockResolvedValue({ authorization_url: 'http://127.0.0.1:1/auth' })
    const assign = vi.fn()
    vi.stubGlobal('location', { assign, hostname: '127.0.0.1' })
    const wrapper = mount(SetupView)
    await flushPromises()
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    await wrapper.find('input[value="chatgpt"]').setValue(true)
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    await wrapper.find('button.primary').trigger('click')
    await flushPromises()
    expect(api.chatgptLogin).toHaveBeenCalled()
    expect(assign).toHaveBeenCalledWith('http://127.0.0.1:1/auth')
    vi.unstubAllGlobals()
  })

  it('hors de l’ordinateur hôte, ChatGPT se connecte plus tard sans bloquer l’assistant', async () => {
    api.chatgptStatus.mockResolvedValue({ redirect_uri: 'http://127.0.0.1:8080/auth/callback' })
    vi.stubGlobal('location', { assign: vi.fn(), hostname: '192.168.1.20' })
    const wrapper = mount(SetupView)
    await flushPromises()
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    await wrapper.find('input[value="chatgpt"]').setValue(true)
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.text()).toContain('http://127.0.0.1:8080')
    expect(api.chatgptLogin).not.toHaveBeenCalled()
    await wrapper.find('button.primary').trigger('click')
    expect(replace).toHaveBeenCalledWith('/')
    vi.unstubAllGlobals()
  })

  it('montre l’échec du test sans bloquer', async () => {
    api.testAI.mockResolvedValue({ ok: false, message: 'Connexion impossible.' })
    const wrapper = mount(SetupView)
    await flushPromises()
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    await wrapper.find('input[value="fake"]').setValue(true)
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('Connexion impossible.')
  })

  async function reachLastStep(wrapper: ReturnType<typeof mount>): Promise<void> {
    await flushPromises()
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    await wrapper.find('input[value="fake"]').setValue(true)
    await wrapper.find('form').trigger('submit')
    await flushPromises()
  }

  it('propose de télécharger les programmes de la classe, sans bloquer la suite', async () => {
    api.downloadProgrammes.mockResolvedValue({ downloaded: 20, already: 2, errors: [] })
    const wrapper = mount(SetupView)
    await reachLastStep(wrapper)
    expect(wrapper.text()).toContain('Programmes officiels · Seconde')

    const download = wrapper
      .findAll('button')
      .find((b) => b.text().includes('Télécharger les programmes'))
    expect(download).toBeDefined()
    await download!.trigger('click')
    await flushPromises()
    expect(api.downloadProgrammes).toHaveBeenCalledOnce()
    expect(wrapper.text()).toContain('22 programme(s) prêt(s).')

    await wrapper.find('button.primary').trigger('click')
    expect(replace).toHaveBeenCalledWith('/')
  })

  it('signale les programmes manquants et permet de réessayer', async () => {
    api.downloadProgrammes.mockResolvedValue({ downloaded: 18, already: 0, errors: ['Maths'] })
    const wrapper = mount(SetupView)
    await reachLastStep(wrapper)
    const download = () =>
      wrapper.findAll('button').find((b) => /Télécharger les programmes|Réessayer/.test(b.text()))!
    await download().trigger('click')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('1 n’ont pas pu être téléchargés')
    expect(download().text()).toContain('Réessayer')
  })

  it('montre une erreur de téléchargement sans quitter l’assistant', async () => {
    api.downloadProgrammes.mockRejectedValue(new Error('hors ligne'))
    const wrapper = mount(SetupView)
    await reachLastStep(wrapper)
    const button = wrapper
      .findAll('button')
      .find((b) => b.text().includes('Télécharger les programmes'))!
    await button.trigger('click')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Commencer')
  })
})
