const PALETTE = [
  '#5b6ee1',
  '#2f9b5a',
  '#d4508a',
  '#c98a1e',
  '#8a5ad8',
  '#16958a',
  '#d9534f',
  '#1f8fbf',
]

function themeVariables(dark: boolean): Record<string, string> {
  const variables: Record<string, string> = {
    fontFamily: 'Lexend Variable, system-ui, sans-serif',
    fontSize: '15px',
    primaryColor: dark ? '#262b4a' : '#eceefe',
    primaryTextColor: dark ? '#eceef5' : '#1d2233',
    primaryBorderColor: '#8e98ff',
    lineColor: dark ? '#6b7393' : '#9aa3c0',
    secondaryColor: dark ? '#222634' : '#f5f6fb',
    tertiaryColor: dark ? '#1c1f29' : '#ffffff',
    background: dark ? '#1c1f29' : '#ffffff',
    mainBkg: dark ? '#262b4a' : '#eceefe',
    textColor: dark ? '#eceef5' : '#1d2233',
  }
  PALETTE.forEach((color, index) => {
    variables[`cScale${index}`] = color
    variables[`cScaleLabel${index}`] = '#ffffff'
    variables[`cScaleInv${index}`] = color
  })
  return variables
}

/** Dessine les schémas Mermaid d'un conteneur (bibliothèque chargée à la demande). */
let counter = 0

export async function renderDiagrams(container: HTMLElement): Promise<void> {
  const figures = [...container.querySelectorAll<HTMLElement>('figure[data-diagram]')].filter(
    (figure) => !figure.dataset.rendered,
  )
  if (!figures.length) return
  const { default: mermaid } = await import('mermaid')
  const dark =
    document.documentElement.dataset.theme === 'dark' ||
    (document.documentElement.dataset.theme === 'auto' &&
      window.matchMedia?.('(prefers-color-scheme: dark)').matches)
  mermaid.initialize({
    startOnLoad: false,
    securityLevel: 'strict',
    // Palette douce, accordée à l'application : une couleur par branche de carte mentale.
    theme: 'base',
    themeVariables: themeVariables(dark),
    fontFamily: 'Lexend Variable, system-ui, sans-serif',
  })
  for (const figure of figures) {
    figure.dataset.rendered = 'true'
    const source = figure.querySelector('pre')?.textContent ?? ''
    try {
      const { svg } = await mermaid.render(`diagram-${++counter}`, source)
      figure.innerHTML = svg
    } catch {
      figure.classList.add('diagram-error')
      figure.insertAdjacentHTML(
        'afterbegin',
        '<p class="hint">Ce schéma n’a pas pu être dessiné. Voici sa description :</p>',
      )
    }
  }
}
