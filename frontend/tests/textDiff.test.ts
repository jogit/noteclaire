import { describe, expect, it } from 'vitest'
import { compareNotesAndCourse, summarizeChanges, toPlainText } from '../src/lib/textDiff'

describe('toPlainText', () => {
  it('retire la syntaxe Markdown et normalise les espaces', () => {
    const markdown = '# Titre\n\n- **point** un\n1. deux\n> citation\n\n$f(x) = ax$\n\n---'
    expect(toPlainText(markdown)).toBe('Titre point un deux citation f(x) = ax')
  })

  it('garde les tirets et underscores à l’intérieur du texte', () => {
    expect(toPlainText('x_1 est un indice - pas une liste')).toBe(
      'x_1 est un indice - pas une liste',
    )
  })
})

describe('compareNotesAndCourse', () => {
  it('ne signale rien si seule la mise en forme change', () => {
    const diff = compareNotesAndCourse(
      'Fonctions affines\nf est affine',
      '# Fonctions affines\n\n- f est affine',
    )
    expect(diff.parts.every((part) => part.kind === 'same')).toBe(true)
    expect(diff.netAddedRatio).toBe(0)
  })

  it('montre une correction comme un mot retiré et un mot ajouté', () => {
    const diff = compareNotesAndCourse('la fonction é affine', 'la fonction est affine')
    expect(diff.parts.filter((p) => p.kind === 'removed').map((p) => p.text)).toEqual(['é'])
    expect(diff.parts.filter((p) => p.kind === 'added').map((p) => p.text)).toEqual(['est'])
    expect(diff.netAddedRatio).toBe(0)
  })

  it('mesure le texte ajouté qui ne remplace rien', () => {
    const diff = compareNotesAndCourse(
      'a est le coefficient directeur',
      'a est le coefficient directeur et b est l’ordonnée à l’origine',
    )
    expect(diff.netAddedRatio).toBeGreaterThan(0.4)
  })

  it('mesure le texte des notes perdu dans le cours', () => {
    const diff = compareNotesAndCourse(
      'a est le coefficient directeur et b est l’ordonnée à l’origine',
      '# Fonctions affines',
    )
    expect(diff.netRemovedRatio).toBeGreaterThan(0.8)
    const fixed = compareNotesAndCourse('la fonction é affine', 'la fonction est affine')
    expect(fixed.netRemovedRatio).toBe(0)
  })

  it('ne compte pas les titres ajoutés comme du contenu ajouté', () => {
    const diff = compareNotesAndCourse(
      'a est le coefficient directeur',
      '# Fonctions affines\n\n## Définitions\n\na est le coefficient directeur',
    )
    expect(diff.parts.some((p) => p.kind === 'added')).toBe(true) // toujours affichés
    expect(diff.netAddedRatio).toBe(0)
  })

  it('ne compte pas comme retiré un mot des notes devenu titre', () => {
    const diff = compareNotesAndCourse(
      'Fonctions affines a est le coefficient directeur',
      'a est le coefficient directeur\n\n# Fonctions affines',
    )
    expect(diff.netRemovedRatio).toBe(0)
  })

  it('gère des textes vides', () => {
    expect(compareNotesAndCourse('', '').netAddedRatio).toBe(0)
  })
})

describe('summarizeChanges', () => {
  it('liste les fautes corrigées sans le bruit de mise en forme', () => {
    const summary = summarizeChanges(
      'chap 5 vecteurs\nle vecteur AB a une longeur. la longeur est la norme : racine de x²+y²',
      '# Chapitre 5 — Vecteurs\n\nLe vecteur $\\overrightarrow{AB}$ a une longueur.\n\n' +
        'La longueur est la norme : $\\sqrt{x^2 + y^2}$.',
    )
    expect(summary.corrections).toEqual([{ before: 'longeur', after: 'longueur', count: 2 }])
    expect(summary.added).toEqual([])
    expect(summary.removed).toEqual([])
    expect(summary.rewrites).toEqual([])
    expect(summary.formatting).toBeGreaterThan(0)
  })

  it('signale ce qui est ajouté ou retiré', () => {
    const summary = summarizeChanges(
      'vecteur nul (avec la fleche) : AA = 0',
      'Vecteur nul : AA = 0. Il est colinéaire à tout vecteur.',
    )
    expect(summary.removed).toEqual(['avec la fleche'])
    expect(summary.added).toEqual(['il est colinéaire à tout vecteur'])
  })

  it('traite une abréviation développée comme une correction', () => {
    const summary = summarizeChanges('ex : diamant', 'Exemple : diamant')
    expect(summary.corrections).toEqual([{ before: 'ex', after: 'exemple', count: 1 }])
  })
})

describe('toPlainText — cours enrichi', () => {
  it('ignore encadrés, surlignage, schémas et images', () => {
    const markdown =
      '::: definition Vecteur\nUn ==vecteur== a une direction.\n:::\n\n' +
      '```mermaid\nmindmap\n  root((X))\n```\n\n![schéma](/api/images/1/a.jpg)'
    expect(toPlainText(markdown)).toBe('Un vecteur a une direction.')
  })
})

describe('toPlainText — notes issues d’une photo', () => {
  it('compte une lecture incertaine comme sa première lecture', () => {
    expect(toPlainText('les plantes [?vertes captent|vertes utilisent] la lumière')).toBe(
      'les plantes vertes captent la lumière',
    )
  })
})
