import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { api, setAuthRequiredHandler } from '../src/api/client'
import { ApiError } from '../src/api/errors'

const fetchMock = vi.fn()

function reply(status: number, body?: unknown): Response {
  return new Response(body === undefined ? null : JSON.stringify(body), { status })
}

describe('api client', () => {
  beforeEach(() => {
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
    localStorage.clear()
    setAuthRequiredHandler(() => {})
  })
  afterEach(() => vi.unstubAllGlobals())

  it('lit la réponse JSON et envoie les cookies de session', async () => {
    fetchMock.mockResolvedValue(reply(200, [{ id: 1, name: 'Léa', level: 'seconde' }]))
    expect(await api.students()).toEqual([{ id: 1, name: 'Léa', level: 'seconde' }])
    const [url, options] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/students')
    expect(options).toMatchObject({ method: 'GET', credentials: 'same-origin' })
  })

  it('envoie l’élève choisi dans ce navigateur', async () => {
    localStorage.setItem('noteclaire:student', '7')
    fetchMock.mockResolvedValue(reply(200, []))
    await api.subjects()
    expect(fetchMock.mock.calls[0][1].headers['X-Student-Id']).toBe('7')
  })

  it('n’envoie pas d’élève quand aucun n’est choisi', async () => {
    fetchMock.mockResolvedValue(reply(200, []))
    await api.subjects()
    expect(fetchMock.mock.calls[0][1].headers).not.toHaveProperty('X-Student-Id')
  })

  it('envoie le corps en JSON, ou en formulaire sans forcer le type', async () => {
    fetchMock.mockImplementation(() => Promise.resolve(reply(200, {}))) // une réponse neuve à chaque appel
    await api.createStudent('Léa', 'seconde')
    const json = fetchMock.mock.calls[0][1]
    expect(json.headers['Content-Type']).toBe('application/json')
    expect(JSON.parse(json.body)).toEqual({ name: 'Léa', level: 'seconde' })

    await api.restoreBackupFile(new File(['zip'], 'sauvegarde.zip'))
    const form = fetchMock.mock.calls[1][1]
    expect(form.body).toBeInstanceOf(FormData)
    expect(form.headers).not.toHaveProperty('Content-Type')
  })

  it('traduit une erreur de l’API en ApiError avec son code', async () => {
    fetchMock.mockResolvedValue(reply(409, { error: { code: 'last_student', message: 'x' } }))
    await expect(api.deleteStudent(1)).rejects.toMatchObject({
      code: 'last_student',
      status: 409,
    })
  })

  it('prévient quand une connexion est requise', async () => {
    const onAuth = vi.fn()
    setAuthRequiredHandler(onAuth)
    fetchMock.mockResolvedValue(reply(401, { error: { code: 'auth_required', message: '' } }))
    await expect(api.students()).rejects.toBeInstanceOf(ApiError)
    expect(onAuth).toHaveBeenCalledTimes(1)
  })

  it('renvoie une erreur réseau claire quand le serveur ne répond pas', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))
    await expect(api.students()).rejects.toMatchObject({ code: 'network_error', status: 0 })
  })

  it('accepte une réponse vide (204) et un corps d’erreur illisible', async () => {
    fetchMock.mockResolvedValueOnce(reply(204))
    expect(await api.deleteStudent(2)).toBeUndefined()

    fetchMock.mockResolvedValueOnce(new Response('<html>', { status: 502 }))
    await expect(api.students()).rejects.toMatchObject({ code: 'http_502' })
  })

  it('une ressource absente (404) devient null quand le client le prévoit', async () => {
    fetchMock.mockResolvedValue(reply(404, { error: { code: 'not_found', message: '' } }))
    expect(await api.quiz(3)).toBeNull()
  })
})
