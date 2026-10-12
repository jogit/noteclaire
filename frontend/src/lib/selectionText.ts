/**
 * Texte d'une sélection dans le cours affiché, avec les formules remises en LaTeX ($…$).
 *
 * KaTeX garde une copie cachée de chaque formule (MathML) : sans ce traitement, le texte
 * sélectionné contient chaque formule en double (« g · L − 1 g·L −1 »).
 */
export function selectionText(range: Range): string {
  const fragment = range.cloneContents()
  for (const formula of fragment.querySelectorAll('.katex')) {
    const latex = formula.querySelector('annotation[encoding="application/x-tex"]')?.textContent
    if (latex) {
      formula.replaceWith(`$${latex.trim()}$`)
    } else {
      // Formule sélectionnée en partie : on garde seulement le texte visible.
      formula.querySelectorAll('.katex-mathml').forEach((copy) => copy.remove())
    }
  }
  fragment.querySelectorAll('.katex-mathml').forEach((copy) => copy.remove())
  const container = document.createElement('div')
  container.append(fragment)
  // Un saut de ligne entre les blocs (paragraphes, lignes de tableau…).
  container
    .querySelectorAll('p, li, tr, h1, h2, h3, h4, aside, blockquote')
    .forEach((block) => block.append('\n'))
  return (
    container.textContent
      ?.replace(/[ \t]+/g, ' ')
      .replace(/\n\s*\n+/g, '\n')
      .trim() ?? ''
  )
}
