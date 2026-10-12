/// <reference types="vitest/config" />
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [vue()],
  build: {
    // Les schémas (Mermaid, ELK, Cytoscape) pèsent plus de 500 Ko mais ne se chargent qu'à l'affichage
    // d'un schéma : l'avertissement ne s'applique pas.
    chunkSizeWarningLimit: 1600,
  },
  server: {
    port: 5173,
    proxy: { '/api': 'http://localhost:8000', '/auth': 'http://localhost:8000' },
  },
  test: {
    environment: 'jsdom',
    include: ['tests/**/*.test.ts'],
    setupFiles: ['tests/setup.ts'],
  },
})
