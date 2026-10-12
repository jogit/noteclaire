import { createApp } from 'vue'
import App from './App.vue'
import { syncStudentCookie } from './lib/currentStudent'
import { router } from './router'
import '@fontsource-variable/lexend'
import './styles.css'

syncStudentCookie()
createApp(App).use(router).mount('#app')

// Application installable (écran d'accueil du téléphone) : seulement en HTTPS ou sur localhost.
if (import.meta.env.PROD && 'serviceWorker' in navigator && window.isSecureContext) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {})
  })
}
