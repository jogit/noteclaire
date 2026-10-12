import { afterEach, describe, expect, it, vi } from 'vitest'
import { getStudentId, setStudentId } from '../src/lib/currentStudent'

describe('élève choisi dans ce navigateur', () => {
  afterEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('mémorise et relit l’identifiant', () => {
    expect(getStudentId()).toBeUndefined()
    setStudentId(5)
    expect(getStudentId()).toBe(5)
  })

  it('ignore une valeur invalide', () => {
    for (const bad of ['abc', '0', '-3', '1.5', '']) {
      localStorage.setItem('noteclaire:student', bad)
      expect(getStudentId()).toBeUndefined()
    }
  })

  it('reste utilisable quand le stockage du navigateur est refusé', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('refusé')
    })
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('refusé')
    })
    expect(getStudentId()).toBeUndefined()
    expect(() => setStudentId(2)).not.toThrow()
  })
})
