import { test as base } from '@playwright/test'

export { expect } from '@playwright/test'

/** Comme `test`, mais l'assistant de premier lancement ne s'interpose pas (IA non configurée). */
export const test = base.extend({
  page: async ({ page }, use) => {
    await page.route('**/api/setup/status', async (route) => {
      const response = await route.fetch()
      await route.fulfill({ response, json: { ...(await response.json()), needs_setup: false } })
    })
    await use(page)
  },
})
