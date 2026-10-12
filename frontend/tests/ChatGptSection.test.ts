import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ChatGptSection from '../src/components/ChatGptSection.vue'

const api = vi.hoisted(() => ({
  chatgptStatus: vi.fn(),
  chatgptLogin: vi.fn(),
  chatgptModels: vi.fn(),
  chatgptSetModel: vi.fn(),
  chatgptLogout: vi.fn(),
}))
const route = vi.hoisted(() => ({ query: {} as Record<string, string> }))
const replace = vi.hoisted(() => vi.fn())
vi.mock('../src/api/client', () => ({ api }))
vi.mock('vue-router', async (importOriginal) => ({
  ...(await importOriginal<typeof import('vue-router')>()),
  useRoute: () => route,
  useRouter: () => ({ replace }),
}))

const disconnected = {
  ai_provider: 'chatgpt',
  connected: false,
  email: '',
  name: '',
  model: '',
  needs_reauth: false,
  redirect_uri: 'http://127.0.0.1:8080/auth/callback',
}
const connected = {
  ...disconnected,
  connected: true,
  email: 'eleve@example.org',
  name: 'Élève',
  model: 'gpt-6-luna',
}

async function mountView() {
  const wrapper = mount(ChatGptSection)
  await flushPromises()
  return wrapper
}

const button = (wrapper: Awaited<ReturnType<typeof mountView>>, text: string) =>
  wrapper.findAll('button').find((b) => b.text().includes(text))!

describe('ChatGptSection', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    route.query = {}
  })
  afterEach(() => vi.unstubAllGlobals())

  it('lance la connexion en redirigeant vers chatgpt.com', async () => {
    api.chatgptStatus.mockResolvedValue(disconnected)
    api.chatgptLogin.mockResolvedValue({ authorization_url: 'https://auth.openai.com/x' })
    const assign = vi.fn()
    vi.stubGlobal('location', { ...window.location, assign, hostname: '127.0.0.1' })
    const wrapper = await mountView()

    await button(wrapper, 'Continue with ChatGPT').trigger('click')
    await flushPromises()

    expect(assign).toHaveBeenCalledWith('https://auth.openai.com/x')
  })

  it('explique où se connecter depuis un autre appareil, avec le port du serveur', async () => {
    api.chatgptStatus.mockResolvedValue({
      ...disconnected,
      redirect_uri: 'http://127.0.0.1:8081/auth/callback',
    })
    vi.stubGlobal('location', { ...window.location, hostname: '192.168.1.20' })
    const wrapper = await mountView()

    expect(wrapper.text()).toContain('http://127.0.0.1:8081')
    expect(wrapper.text()).toContain('pas localhost')
    expect(wrapper.findAll('button').some((b) => b.text().includes('Continue with ChatGPT'))).toBe(
      false,
    )
  })

  it('refuse aussi localhost : OpenAI ne renvoie que vers 127.0.0.1', async () => {
    api.chatgptStatus.mockResolvedValue(disconnected)
    vi.stubGlobal('location', { ...window.location, hostname: 'localhost' })
    const wrapper = await mountView()

    expect(wrapper.text()).toContain('pas localhost')
  })

  it('affiche le compte connecté et enregistre le modèle choisi', async () => {
    api.chatgptStatus.mockResolvedValue(connected)
    api.chatgptModels.mockResolvedValue([
      { slug: 'gpt-6-luna', display_name: 'GPT-6 Luna' },
      { slug: 'gpt-6-sol', display_name: 'GPT-6 Sol' },
    ])
    api.chatgptSetModel.mockResolvedValue(undefined)
    const wrapper = await mountView()

    expect(wrapper.text()).toContain('Connecté : Élève')
    expect(wrapper.text()).toContain('Using ChatGPT plan')
    expect(wrapper.find('a[href="https://chatgpt.com/settings/usage"]').text()).toBe('Manage usage')
    await wrapper.find('#chatgpt-model').setValue('gpt-6-sol')
    await button(wrapper, 'Enregistrer').trigger('click')
    await flushPromises()

    expect(api.chatgptSetModel).toHaveBeenCalledWith('gpt-6-sol')
    expect(wrapper.find('[role="status"]').text()).toContain('Modèle enregistré')
  })

  it('reste masquée quand l’IA choisie n’est pas ChatGPT', async () => {
    api.chatgptStatus.mockResolvedValue({ ...disconnected, ai_provider: 'openai' })
    const wrapper = await mountView()
    expect(wrapper.find('section').exists()).toBe(false)
  })

  it('affiche le résultat du retour de connexion', async () => {
    route.query = { chatgpt: 'erreur', code: 'invalid_state' }
    api.chatgptStatus.mockResolvedValue(disconnected)
    const wrapper = await mountView()
    expect(wrapper.find('[role="alert"]').text()).toContain('Cette connexion a expiré')
    expect(replace).toHaveBeenCalledWith({ query: { onglet: 'ia' } })
  })

  it('prévient si la révocation n’a pas pu être confirmée', async () => {
    api.chatgptStatus.mockResolvedValueOnce(connected).mockResolvedValue(disconnected)
    api.chatgptModels.mockResolvedValue([])
    api.chatgptLogout.mockResolvedValue({ revoked: false })
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const wrapper = await mountView()

    await button(wrapper, 'Se déconnecter').trigger('click')
    await flushPromises()

    expect(wrapper.find('[role="status"]').text()).toContain('n’a pas pu être confirmée')
  })
})
