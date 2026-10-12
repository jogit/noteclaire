import { describe, expect, it } from 'vitest'
import {
  countSpots,
  docToNotes,
  insertFigures,
  notesToDoc,
  parseSpot,
  photoTextToNotes,
  spotMarker,
} from '../src/lib/notesFormat'

describe('format des notes', () => {
  it('écrit et relit les repères de passages incertains', () => {
    expect(spotMarker({ guess: 'cellule', options: ['celule', 'cellule'] })).toBe(
      '[?cellule|celule]',
    )
    expect(spotMarker({ guess: '', options: ['noyau'] })).toBe('[?|noyau]')
    expect(spotMarker({ guess: '', options: [] })).toBe('[illisible]')
    expect(parseSpot('[?cellule|celule]')).toEqual({ guess: 'cellule', options: ['celule'] })
    expect(parseSpot('[illisible]')).toEqual({ guess: '', options: [] })
  })

  it('transforme la réponse de la photo en notes', () => {
    expect(
      photoTextToNotes('les plantes [?] la lumière\n[?] rophylle', [
        { guess: 'vertes captent', options: ['vertes utilisent'] },
        { guess: '', options: [] },
      ]),
    ).toBe('les plantes [?vertes captent|vertes utilisent] la lumière\n[illisible] rophylle')
  })

  it('fait l’aller-retour notes → éditeur → notes sans rien changer', () => {
    const notes =
      'Chap 3 : la cellule\n\n- la [?cellule|celule] est l’unité du [illisible]\n' +
      '![Schéma de la cellule](/api/images/3/abc.jpg)\n**pas du Markdown** 5 * 3 = 15'
    expect(docToNotes(notesToDoc(notes))).toBe(notes)
  })

  it('compte les passages à vérifier', () => {
    expect(countSpots('a [?b|c] d [illisible] e [schéma : f]')).toBe(2)
  })
})

describe('insertFigures', () => {
  const url = (n: number) => `/api/images/3/${String(n).repeat(32)}.jpg`

  it('remplace le repère de chaque schéma découpé, par son rang, et laisse les autres', () => {
    const text = 'a\n[schéma : un]\nb\n[schema : deux]\nc\n[schéma : trois]'
    const result = insertFigures(text, [
      { index: 0, url: url(1) },
      { index: 2, url: url(3) },
    ])
    expect(result).toBe(`a\n![un](${url(1)})\nb\n[schema : deux]\nc\n![trois](${url(3)})`)
  })

  it('met l’image seule sur sa ligne et ne multiplie pas les lignes vides', () => {
    expect(insertFigures('avant [schéma : x] après', [{ index: 0, url: url(1) }])).toBe(
      `avant \n![x](${url(1)})\n après`,
    )
    expect(insertFigures('a\n\n[schéma : x]\n\nb', [{ index: 0, url: url(1) }])).toBe(
      `a\n\n![x](${url(1)})\n\nb`,
    )
  })

  it('ne change rien sans schéma découpé', () => {
    expect(insertFigures('texte [schéma : x]', [])).toBe('texte [schéma : x]')
  })
})
