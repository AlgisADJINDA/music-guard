import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path:      '/',
    name:      'home',
    component: () => import('@/views/HomeView.vue'),
    meta:      { title: 'Accueil — MusicGuard' }
  },
  {
    path:      '/detection',
    name:      'detection',
    component: () => import('@/views/DetectionView.vue'),
    meta:      { title: 'Détection — MusicGuard' }
  },
  {
    path:      '/redevances',
    name:      'redevances',
    component: () => import('@/views/RedevancesView.vue'),
    meta:      { title: 'Redevances — MusicGuard' }
  },
  {
    path:      '/:pathMatch(.*)*',
    redirect:  '/'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0, behavior: 'smooth' })
})

// Mise à jour du titre de page
router.afterEach((to) => {
  document.title = to.meta.title || 'MusicGuard'
})

export default router