import { expect, test } from '@playwright/test'

// Les appels de configuration sont simulés : ce test ne modifie ni l'IA ni les élèves réels.
test('premier lancement : l’assistant s’ouvre et guide jusqu’à l’application', async ({ page }) => {
  const needsSetup = {
    needs_setup: true,
    ai_provider: 'openai',
    has_openai_key: false,
    local_ai_base_url: 'http://localhost:11434/v1',
    local_ai_model: 'qwen3:8b',
    chatgpt_connected: false,
  }
  await page.route('**/api/setup/status', (route) => route.fulfill({ json: needsSetup }))
  await page.route('**/api/setup/ai', (route) => route.fulfill({ json: needsSetup }))
  await page.route('**/api/setup/ai/test', (route) =>
    route.fulfill({ json: { ok: true, message: 'Connexion réussie.' } }),
  )
  await page.route('**/api/students/*', (route) =>
    route.fulfill({ json: { id: 1, name: 'Léa', level: 'seconde', adaptation_notes: '' } }),
  )

  await page.goto('/')
  await expect(page).toHaveURL(/\/bienvenue/)
  await expect(page.getByRole('heading', { name: 'Bienvenue' })).toBeVisible()

  await page.getByLabel('Prénom de l’élève').fill('Léa')
  await page.getByRole('button', { name: 'Continuer' }).click()
  await page.getByText('Essayer sans IA').click()
  await page.getByRole('button', { name: 'Enregistrer et tester' }).click()
  await expect(page.getByText('Connexion réussie.')).toBeVisible()
  await page.getByRole('button', { name: 'Commencer' }).click()
  await expect(page).toHaveURL(/\/$/)
})
