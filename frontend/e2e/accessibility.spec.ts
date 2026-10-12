import AxeBuilder from '@axe-core/playwright'
import type { Page } from '@playwright/test'
import { expect, test } from './fixtures'

// Contrôle automatique (axe) : contrastes, noms des boutons, libellés des champs, structure.
// Les pages sont vérifiées dans chaque thème et avec l'espacement « aéré ».
const PAGES = ['/', '/reglages', '/reglages?onglet=ia', '/reglages?onglet=affichage', '/documents']
// Les trois étapes d'un chapitre (le chapitre d'essai est créé puis supprimé par le test).
const CHAPTER_TABS = ['notes', 'cours', 'reviser']
const PREFIX = 'Essai accessibilité e2e'
const THEMES = ['light', 'cream', 'dark']

async function checkPage(page: Page, url: string, theme: string): Promise<void> {
  await page.goto(url)
  await page.waitForLoadState('networkidle')
  const { violations } = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
    .analyze()
  const serious = violations.filter((v) => v.impact === 'serious' || v.impact === 'critical')
  expect(
    serious.map((v) => `${v.id} (${v.nodes.length}) : ${v.nodes[0]?.target.join(' ')}`),
    `${url} en thème ${theme}`,
  ).toEqual([])
}

for (const theme of THEMES) {
  test(`accessibilité des pages principales : thème ${theme}`, async ({ page, request }) => {
    await page.addInitScript((value) => {
      localStorage.setItem('noteclaire:theme', value)
      localStorage.setItem('noteclaire:spacing', 'large')
    }, theme)

    for (const url of PAGES) await checkPage(page, url, theme)

    const subjects: { id: number }[] = await (await request.get('/api/subjects')).json()
    const created = await request.post('/api/chapters', {
      data: { subject_id: subjects[0].id, title: `${PREFIX} ${Date.now()}` },
    })
    const chapter: { id: number } = await created.json()
    try {
      for (const tab of CHAPTER_TABS) {
        await checkPage(page, `/chapitres/${chapter.id}?onglet=${tab}`, theme)
      }
    } finally {
      await request.delete(`/api/chapters/${chapter.id}`)
      await request.delete(`/api/trash/${chapter.id}`)
    }
  })
}
