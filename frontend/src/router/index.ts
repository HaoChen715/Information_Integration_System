import { createRouter, createWebHistory } from 'vue-router'

import { getToken } from '../api/client'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/oidc-callback',
      name: 'oidc-callback',
      component: () => import('../views/OidcCallbackView.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      name: 'dashboard',
      component: () => import('../views/DashboardView.vue'),
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
})

router.beforeEach((to) => {
  const authenticated = Boolean(getToken())
  if (!to.meta.public && !authenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'login' && authenticated) {
    return { name: 'dashboard' }
  }
  return true
})

export default router
