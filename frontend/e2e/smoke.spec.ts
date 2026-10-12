import { expect, test } from './fixtures'

const PREFIX = 'Essai e2e'

// Même en cas d'échec, ne laisse aucun chapitre de test dans les données de l'utilisateur.
test.afterEach(async ({ request }) => {
  const chapters: { id: number; title: string }[] = await (
    await request.get('/api/chapters')
  ).json()
  for (const chapter of chapters.filter((c) => c.title.startsWith(PREFIX))) {
    await request.delete(`/api/chapters/${chapter.id}`)
  }
  // Les chapitres supprimés vont à la corbeille : on les efface pour de bon.
  const trash: { id: number; title: string }[] = await (await request.get('/api/trash')).json()
  for (const chapter of trash.filter((c) => c.title.startsWith(PREFIX))) {
    await request.delete(`/api/trash/${chapter.id}`)
  }
})

// Parcours principal sans IA : n'utilise que des fonctions qui ne consomment pas de crédit.
test('créer un chapitre, saisir des notes, les retrouver par la recherche', async ({ page }) => {
  const title = `${PREFIX} ${Date.now()}`
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(String(error)))

  await page.goto('/')
  await page.getByRole('navigation').getByRole('link', { name: /SVT/ }).click()
  await expect(page.getByRole('heading', { level: 1, name: 'SVT' })).toBeVisible()
  await page.getByRole('button', { name: 'Nouveau chapitre' }).first().click()
  await page.getByLabel('Titre du chapitre').fill(title)
  await page.getByRole('button', { name: 'Créer' }).click()

  await expect(page.getByRole('heading', { level: 1 })).toHaveText(title)
  await expect(page.getByRole('tab', { name: /Mes notes/ })).toHaveAttribute(
    'aria-selected',
    'true',
  )
  // Les notes sont un éditeur (texte simple, images, passages à vérifier).
  const notes = page.getByRole('textbox', { name: 'Mes notes' })
  await notes.click()
  await page.keyboard.type('La mitochondrie produit l’énergie de la cellule.')
  await expect(page.getByText('Sauvegardé')).toBeVisible({ timeout: 5000 })

  await page.reload()
  await expect(notes).toHaveText(/mitochondrie/)

  await page.getByLabel('Rechercher dans mes cours').fill('mitochondrie')
  await page.getByLabel('Rechercher dans mes cours').press('Enter')
  await expect(page.getByRole('link', { name: new RegExp(title) })).toBeVisible()

  await page.getByRole('link', { name: new RegExp(title) }).click()
  await page.getByRole('button', { name: "Plus d'actions" }).click()
  page.once('dialog', (dialog) => dialog.accept())
  await page.getByRole('button', { name: 'Supprimer ce chapitre' }).click()
  await expect(page.getByRole('heading', { level: 1, name: 'SVT' })).toBeVisible()
  expect(errors).toEqual([])
})

// Nécessite Internet : les programmes sont téléchargés depuis les sites officiels. Sauté en CI
// (réseau et lenteur des sites hors de notre contrôle) ; le téléchargement est testé côté serveur.
test('télécharger les programmes officiels les ajoute aux documents', async ({ page }) => {
  test.skip(!!process.env.CI, 'Dépend des sites de l’Éducation nationale')
  test.setTimeout(150_000)
  await page.goto('/documents')
  await page.getByRole('button', { name: 'Télécharger les programmes officiels' }).click()
  await expect(page.getByText(/programme\(s\) téléchargé|déjà présents/)).toBeVisible({
    timeout: 120_000,
  })
  await expect(page.getByText('Programme de mathématiques de seconde')).toBeVisible()
})
