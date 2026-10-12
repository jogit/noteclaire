import { createRouter, createWebHistory } from 'vue-router'
import { api, setAuthRequiredHandler } from './api/client'
import { isSetupChecked, markSetupDone } from './lib/setupState'
import HomeView from './views/HomeView.vue'
import LoginView from './views/LoginView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    {
      path: '/matieres/:slug',
      name: 'subject',
      component: () => import('./views/SubjectView.vue'),
      props: true,
    },
    {
      path: '/chapitres/:id',
      name: 'chapter',
      component: () => import('./views/ChapterView.vue'),
      props: true,
    },
    {
      path: '/chapitres/:id/imprimer',
      name: 'print',
      component: () => import('./views/PrintView.vue'),
      props: true,
      meta: { bare: true },
    },
    {
      path: '/documents',
      name: 'references',
      component: () => import('./views/ReferencesView.vue'),
    },
    { path: '/recherche', name: 'search', component: () => import('./views/SearchView.vue') },
    { path: '/reglages', name: 'settings', component: () => import('./views/SettingsView.vue') },
    { path: '/corbeille', name: 'trash', component: () => import('./views/TrashView.vue') },
    {
      path: '/bienvenue',
      name: 'setup',
      component: () => import('./views/SetupView.vue'),
      meta: { bare: true },
    },
    { path: '/connexion', name: 'login', component: LoginView, meta: { bare: true } },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

let authChecked = false

router.beforeEach(async (to) => {
  if (to.name === 'login') return true
  if (!authChecked) {
    try {
      const status = await api.authStatus()
      authChecked = true
      if (status.auth_required && !status.authenticated) {
        return { name: 'login', query: { suite: to.fullPath } }
      }
    } catch {
      // Serveur injoignable : la page affichera l'erreur.
      return true
    }
  }
  // Premier lancement : tant que l'IA n'est pas choisie, l'assistant s'affiche.
  if (!isSetupChecked() && to.name !== 'setup') {
    try {
      const setup = await api.setupStatus()
      if (!setup.needs_setup) markSetupDone()
      if (setup.needs_setup) return { name: 'setup' }
    } catch {
      // On laisse l'application s'ouvrir.
    }
  }
  return true
})

setAuthRequiredHandler(() => {
  const current = router.currentRoute.value
  if (current.name !== 'login') {
    router.push({ name: 'login', query: { suite: current.fullPath } })
  }
})
