import type { Suggestion } from '../src/api/types'

export const suggestion = (id: number, overrides: Partial<Suggestion> = {}): Suggestion => ({
  id,
  chapter_id: 1,
  type: 'correction',
  original_text: 'b est la pente',
  suggested_text: 'a est le coefficient directeur',
  reason: 'La définition semble inversée.',
  confidence: 0.9,
  status: 'pending',
  created_at: '2026-10-03T20:00:00Z',
  decided_at: null,
  source_reference: '',
  ...overrides,
})
