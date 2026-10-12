import { diffWords } from 'diff'

type DiffPart = { kind: 'same' | 'added' | 'removed'; text: string }

export interface TextDiff {
  parts: DiffPart[]
  /** Part du cours composée de mots ajoutés sans remplacer un mot des notes (0 à 1). */
  netAddedRatio: number
  /** Part des notes retirée sans être remplacée (0 à 1). */
  netRemovedRatio: number
}

/** Au-delà de ce ratio, on avertit que le cours contient du texte absent des notes. */
export const ADDED_TEXT_WARNING_RATIO = 0.1

/** Au-delà de ce ratio, on avertit que le cours a perdu une partie des notes. */
export const REMOVED_TEXT_WARNING_RATIO = 0.15

/** Retire la syntaxe Markdown et normalise les espaces, pour ne comparer que le texte. */
export function toPlainText(markdown: string): string {
  return markdown
    .replace(/```mermaid[\s\S]*?```/g, '') // schémas : pas du texte des notes
    .replace(/!\[[^\]]*\]\([^)]*\)/g, '') // images
    .replace(/\[\?([^|\]\n]*)(?:\|[^\]\n]*)?\]/g, '$1') // lecture incertaine : 1re lecture
    .split('\n')
    .filter((line) => !/^\s*:::/.test(line)) // marqueurs d'encadrés
    .map((line) =>
      line
        .replace(/^\s{0,3}#{1,6}\s+/, '')
        .replace(/^\s*>\s?/, '')
        .replace(/^\s*(?:[-*+]|\d+[.)])\s+/, '')
        .replace(/^\s*(?:-{3,}|\*{3,}|_{3,})\s*$/, ''),
    )
    .join('\n')
    .replace(/\*\*|__|\*|`|\$\$?|==/g, '')
    .replace(/\s+/g, ' ')
    .trim()
}

function splitWords(text: string): string[] {
  return text.split(/\s+/).filter(Boolean)
}

const HEADING = /^\s{0,3}#{1,6}\s+/

/** Mots des titres du cours : les titres sont de la structure, pas du contenu ajouté. */
function headingWords(course: string): string[] {
  return course
    .split('\n')
    .filter((line) => HEADING.test(line))
    .flatMap((line) => splitWords(toPlainText(line)))
}

/** Comparaison mot à mot, déterministe, entre les notes et le cours (SPEC §13.1). */
export function compareNotesAndCourse(notes: string, course: string): TextDiff {
  const parts: DiffPart[] = diffWords(toPlainText(notes), toPlainText(course)).map((change) => ({
    kind: change.added ? 'added' : change.removed ? 'removed' : 'same',
    text: change.value,
  }))

  const words = (keep: (part: DiffPart) => boolean) =>
    splitWords(
      parts
        .filter(keep)
        .map((p) => p.text)
        .join(' '),
    )
  // Les mots des titres ne comptent pas comme ajoutés ; un mot des notes devenu titre
  // (ex. « Fonctions affines » en tête des notes) ne compte pas comme retiré.
  const titles = headingWords(course)
  const notTitle = (pool: string[]) => (word: string) => {
    const index = pool.indexOf(word)
    if (index === -1) return true
    pool.splice(index, 1) // chaque mot de titre n'excuse qu'un seul mot
    return false
  }
  const added = words((p) => p.kind === 'added').filter(notTitle([...titles])).length
  const removed = words((p) => p.kind === 'removed').filter(notTitle([...titles])).length
  const courseWords = words((p) => p.kind !== 'removed').filter(notTitle([...titles])).length
  const notesWords = words((p) => p.kind !== 'added').length

  return {
    parts,
    netAddedRatio: courseWords === 0 ? 0 : Math.max(0, added - removed) / courseWords,
    netRemovedRatio: notesWords === 0 ? 0 : Math.max(0, removed - added) / notesWords,
  }
}

// --- Résumé lisible des changements (« Voir les modifications ») -------------------------

interface WordChange {
  before: string
  after: string
  count: number
}

export interface ChangeSummary {
  /** Mots corrigés (orthographe, accords) : « longeur → longueur ». */
  corrections: WordChange[]
  /** Passages reformulés : plusieurs mots remplacés par d'autres. */
  rewrites: WordChange[]
  /** Texte présent dans le cours mais absent des notes (titres exclus). */
  added: string[]
  /** Texte des notes absent du cours. */
  removed: string[]
  /** Retouches sans effet sur le sens : ponctuation, majuscules, formules, mise en forme. */
  formatting: number
}

const LATEX_WORDS: Record<string, string> = {
  sqrt: ' racine ',
  times: ' x ',
  cdot: ' x ',
  infty: ' infini ',
}
// Fonctions écrites \det, \sin… dans les formules : on garde leur nom.
for (const name of ['det', 'sin', 'cos', 'tan', 'ln', 'log', 'exp', 'lim', 'max', 'min']) {
  LATEX_WORDS[name] = ` ${name} `
}

/** Abréviations de notes que la mise au propre remplace par une notation. */
const NOTATION_ABBREVIATIONS = new Set(['vect', 'ssi', 'cad', 'tq'])

const SUPERSCRIPTS: Record<string, string> = { '²': '2', '³': '3', '⁴': '4', '½': '1/2' }

/**
 * Texte comparable : sans titres, sans Markdown, sans LaTeX, sans ponctuation ni majuscules.
 * Les accents sont gardés : les corriger est une vraie correction d'orthographe.
 */
function toComparable(markdown: string): string {
  const withoutHeadings = markdown
    .split('\n')
    .filter((line) => !HEADING.test(line))
    .join('\n')
  return toPlainText(
    withoutHeadings
      .replace(/\\(?:text|mathrm|textbf|operatorname)\{([^}]*)\}/g, '$1')
      .replace(/\\(?:overrightarrow|vec|overline|widehat)\{([^}]*)\}/g, '$1')
      .replace(/\\([a-zA-Z]+)/g, (_, name: string) => LATEX_WORDS[name] ?? ' ')
      .replace(/[²³⁴½]/g, (c) => SUPERSCRIPTS[c] ?? c),
  )
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, ' ')
    .replace(/(\p{L})(\p{N})/gu, '$1 $2')
    .replace(/(\p{N})(\p{L})/gu, '$1 $2')
    .replace(/\s+/g, ' ')
    .trim()
}

/** Un passage sans aucun mot d'au moins 3 lettres (variables, nombres) : mise en forme. */
function hasRealWord(text: string): boolean {
  return /\p{L}{3,}/u.test(text)
}

const comparableWord = (word: string) =>
  word
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^\p{L}\p{N}]+/gu, '')

/** Égalité « au sens près » : seuls la casse et la ponctuation diffèrent. */
function sameMeaning(before: string, after: string): boolean {
  const strip = (text: string) =>
    text
      .toLowerCase()
      .replace(/[^\p{L}\p{N}]+/gu, '')
      .trim()
  return strip(before) === strip(after)
}

function levenshtein(a: string, b: string): number {
  const row = Array.from({ length: b.length + 1 }, (_, i) => i)
  for (let i = 1; i <= a.length; i++) {
    let previous = row[0]!
    row[0] = i
    for (let j = 1; j <= b.length; j++) {
      const current = row[j]!
      row[j] = Math.min(row[j]! + 1, row[j - 1]! + 1, previous + (a[i - 1] === b[j - 1] ? 0 : 1))
      previous = current
    }
  }
  return row[b.length]!
}

/** Correction d'un ou deux mots proches (fautes, accents, accords, abréviations). */
function isCorrection(before: string, after: string): boolean {
  if (before.length >= 2 && after.startsWith(before) && !before.includes(' ')) return true
  const a = before.trim().split(/\s+/)
  const b = after.trim().split(/\s+/)
  if (a.length > 3 || b.length > 3) return false
  const x = before.toLowerCase().trim()
  const y = after.toLowerCase().trim()
  const longest = Math.max(x.length, y.length)
  // Mots très courts : homophones fréquents (é/est, a/à, ces/ses).
  const tolerance = longest <= 4 ? 3 : Math.max(2, Math.ceil(longest * 0.4))
  return levenshtein(x, y) <= tolerance
}

function addTo(list: WordChange[], before: string, after: string): void {
  const existing = list.find((c) => c.before === before && c.after === after)
  if (existing) existing.count++
  else list.push({ before, after, count: 1 })
}

/** Range un changement (texte retiré → texte ajouté) dans la catégorie qui lui correspond. */
function classifyChange(
  summary: ChangeSummary,
  before: string,
  after: string,
  inTitle: (word: string) => boolean,
): void {
  if (sameMeaning(before, after) || (!hasRealWord(before) && !hasRealWord(after))) {
    summary.formatting++
  } else if (before && after) {
    addTo(isCorrection(before, after) ? summary.corrections : summary.rewrites, before, after)
  } else if (after) {
    // Les mots repris dans les titres sont de la structure, pas du contenu ajouté.
    const content = after.split(/\s+/).filter((w) => !inTitle(w))
    if (hasRealWord(content.join(' '))) summary.added.push(after)
    else summary.formatting++
  } else {
    const content = before.split(/\s+/).filter((w) => !inTitle(w) && !NOTATION_ABBREVIATIONS.has(w))
    if (hasRealWord(content.join(' '))) summary.removed.push(before)
    else summary.formatting++
  }
}

export function summarizeChanges(notes: string, course: string): ChangeSummary {
  const summary: ChangeSummary = {
    corrections: [],
    rewrites: [],
    added: [],
    removed: [],
    formatting: 0,
  }
  const titleWords = headingWords(course).map(comparableWord).filter(Boolean)
  // Un mot repris dans un titre, même abrégé dans les notes (« chap » → « Chapitre »).
  const inTitle = (word: string) => {
    const w = comparableWord(word)
    return !!w && titleWords.some((t) => t === w || (w.length >= 3 && t.startsWith(w)))
  }

  let removedText = ''
  let addedText = ''
  const flush = () => {
    const before = removedText.trim()
    const after = addedText.trim()
    removedText = ''
    addedText = ''
    if (before || after) classifyChange(summary, before, after, inTitle)
  }

  for (const change of diffWords(toComparable(notes), toComparable(course))) {
    if (change.added) addedText += change.value
    else if (change.removed) removedText += change.value
    else if (change.value.trim()) flush()
    else {
      // Espace seul entre deux changements : on le garde dans le même groupe.
      removedText += change.value
      addedText += change.value
    }
  }
  flush()
  return summary
}
