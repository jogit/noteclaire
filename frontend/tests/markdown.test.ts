import { describe, expect, it } from 'vitest'
import { markdownExcerpt, renderMarkdown, replaceSchema } from '../src/lib/markdown'

describe('renderMarkdown', () => {
  it('rend les titres et les listes', () => {
    const html = renderMarkdown('# Titre\n\n- un\n- deux')
    expect(html).toContain('<h1>Titre</h1>')
    expect(html).toContain('<li>un</li>')
  })

  it('rend les formules avec KaTeX', () => {
    expect(renderMarkdown('Soit $f(x) = ax + b$.')).toContain('class="katex"')
    expect(renderMarkdown('$$\\frac{1}{2}$$')).toContain('katex-display')
  })

  it('remplace les <br> par un espace au lieu de les afficher', () => {
    const html = renderMarkdown('| Mot | Sens |\n|---|---|\n| Azur | le ciel<br>⚠ À vérifier |')
    expect(html).toContain('le ciel ⚠ À vérifier')
    expect(html).not.toContain('&lt;br')
  })

  it("n'interprète pas le HTML brut", () => {
    const html = renderMarkdown('<img src=x onerror="alert(1)"> <script>alert(1)</script>')
    expect(html).not.toContain('<img')
    expect(html).not.toContain('<script')
    expect(html).toContain('&lt;script&gt;')
  })

  it('ne plante pas sur une formule invalide', () => {
    expect(() => renderMarkdown('$\\frac{$')).not.toThrow()
  })
})

describe('renderMarkdown — cours enrichi', () => {
  it('rend les encadrés avec leur libellé écrit', () => {
    const html = renderMarkdown('::: definition Vecteur\nUn vecteur a une direction.\n:::')
    expect(html).toContain('class="callout callout-definition"')
    expect(html).toContain('<span class="callout-label">Définition</span> Vecteur')
    expect(html).toContain('<p>Un vecteur a une direction.</p>')
  })

  it('surligne les mots-clés', () => {
    expect(renderMarkdown('Le ==coefficient directeur== est a.')).toContain(
      '<mark>coefficient directeur</mark>',
    )
  })

  it('prépare les schémas Mermaid sans les exécuter', () => {
    const html = renderMarkdown('```mermaid\nmindmap\n  root((Vecteurs))\n```')
    expect(html).toContain('<figure class="diagram" data-diagram>')
    expect(html).toContain('root((Vecteurs))')
  })

  it("n'affiche que les images hébergées par NoteClaire", () => {
    expect(renderMarkdown('![schéma](/api/images/3/abc.jpg)')).toContain(
      'src="/api/images/3/abc.jpg"',
    )
    const external = renderMarkdown('![pixel](https://tracker.example/p.gif)')
    expect(external).not.toContain('<img')
    expect(external).toContain('[image : pixel]')
  })

  it('transforme les [schéma : …] en emplacements numérotés', () => {
    const html = renderMarkdown('Texte [schéma : la cellule] et [Schéma : le noyau].')
    expect(html).toContain('data-schema-index="0"')
    expect(html).toContain('Schéma à ajouter :</strong> la cellule')
    expect(html).toContain('data-schema-index="1"')
  })
})

describe('replaceSchema', () => {
  it('remplace le bon emplacement par une image', () => {
    expect(replaceSchema('a [schéma : un] b [schéma : deux]', 1, '/api/images/1/x.jpg')).toBe(
      'a [schéma : un] b ![deux](/api/images/1/x.jpg)',
    )
  })
})

describe('markdownExcerpt', () => {
  it('ne coupe ni une formule ni un mot', () => {
    expect(markdownExcerpt('Court passage $x^2$.')).toBe('Court passage $x^2$.')
    const long = 'On voit la lumière entre $400\\ \\mathrm{nm}$ et $800\\ \\mathrm{nm}$ environ.'
    expect(markdownExcerpt(long, 50)).toBe('On voit la lumière entre $400\\ \\mathrm{nm}$ et…')
    expect(markdownExcerpt(long, 30)).toBe('On voit la lumière entre…')
    expect(markdownExcerpt('Une phrase vraiment très longue', 12)).toBe('Une phrase…')
  })

  it('retire les marques de bloc et met tout sur une ligne', () => {
    expect(markdownExcerpt('## Titre\n- point un\n- point deux')).toBe('Titre point un point deux')
  })
})
