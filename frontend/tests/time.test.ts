import { describe, expect, it } from 'vitest'
import { timeAgo } from '../src/lib/time'

describe('timeAgo', () => {
  const now = new Date('2026-10-04T12:00:00Z')

  it('exprime une durée relative en français', () => {
    expect(timeAgo('2026-10-04T11:59:50Z', now)).toBe('à l’instant')
    expect(timeAgo('2026-10-04T09:00:00Z', now)).toBe('il y a 3 heures')
    expect(timeAgo('2026-10-03T12:00:00Z', now)).toBe('hier')
  })
})
