import { defineConfig } from '@playwright/test'

// Tests de bout en bout sur l'application lancée (docker compose up) : npm run e2e
export default defineConfig({
  testDir: 'e2e',
  use: { baseURL: process.env.BASE_URL ?? 'http://localhost:8080' },
  reporter: 'list',
})
