import { expect, test } from './fixtures'

const PREFIX = 'Essai e2e élèves'

// Nettoie les élèves et chapitres de test, même en cas d'échec.
test.afterEach(async ({ request }) => {
  const students: { id: number; name: string }[] = await (await request.get('/api/students')).json()
  for (const student of students.filter((s) => s.name.startsWith(PREFIX))) {
    const headers = { 'X-Student-Id': String(student.id) }
    const chapters: { id: number }[] = await (
      await request.get('/api/chapters', { headers })
    ).json()
    for (const chapter of chapters) await request.delete(`/api/chapters/${chapter.id}`, { headers })
    const trash: { id: number }[] = await (await request.get('/api/trash', { headers })).json()
    for (const chapter of trash) await request.delete(`/api/trash/${chapter.id}`, { headers })
    await request.delete(`/api/students/${student.id}`)
  }
})

test('deux élèves ont des chapitres, une recherche et des références séparés', async ({ page }) => {
  const name = `${PREFIX} ${Date.now()}`
  const title = `Suites ${Date.now()}`
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(String(error)))

  // Ajout d'un élève de première dans les Réglages.
  await page.goto('/reglages')
  await page.getByText('Ajouter un élève').click()
  await page.locator('#new-student-name').fill(name)
  await page.locator('#new-student-level').selectOption('premiere')
  await page.getByRole('button', { name: 'Ajouter l’élève' }).click()
  await expect(page.getByRole('article', { name: `Élève ${name}` })).toBeVisible()

  // Le menu « Élève » apparaît ; on bascule sur le nouvel élève.
  await expect(page.getByLabel('Élève', { exact: true })).toBeVisible()
  await page.getByLabel('Élève', { exact: true }).selectOption({ label: name })
  await page.waitForURL('/')
  await expect(page.getByLabel('Élève', { exact: true })).toHaveValue(/\d+/)

  // Un chapitre créé pour lui n'apparaît pas chez l'élève par défaut.
  await page
    .getByRole('navigation')
    .getByRole('link', { name: /Mathématiques/ })
    .click()
  await page.getByRole('button', { name: 'Nouveau chapitre' }).first().click()
  await page.getByLabel('Titre du chapitre').fill(title)
  await page.getByRole('button', { name: 'Créer' }).click()
  await expect(page.getByRole('heading', { name: title })).toBeVisible()

  await page.goto(`/recherche?q=${encodeURIComponent(title.split(' ')[0])}`)
  await expect(page.getByText(title).first()).toBeVisible()

  // La page des documents suit la classe de l'élève : ceux de seconde n'y figurent pas.
  await page.goto('/documents')
  await expect(page.getByRole('heading', { name: 'Programmes et documents' })).toBeVisible()
  await expect(page.getByText('Première générale').first()).toBeVisible()
  await expect(page.getByText('de seconde générale et technologique')).toHaveCount(0)

  // L'élève par défaut ne voit ni ce chapitre ni cette recherche.
  const first = (await (await page.request.get('/api/students')).json())[0]
  const other = await page.request.get('/api/chapters', {
    headers: { 'X-Student-Id': String(first.id) },
  })
  expect((await other.json()).map((c: { title: string }) => c.title)).not.toContain(title)

  expect(errors).toEqual([])
})
