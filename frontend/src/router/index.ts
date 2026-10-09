import { createRouter, createWebHistory } from 'vue-router'

import { getToken } from '../api/client'
import { useAuthStore } from '../stores/auth'

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
      path: '/records',
      name: 'records',
      component: () => import('../views/RecordsView.vue'),
      meta: { permission: 'record:view' },
    },
    {
      path: '/admin/users',
      name: 'admin-users',
      component: () => import('../views/admin/AdminUsersView.vue'),
      meta: { permission: 'user:view', admin: true },
    },
    {
      path: '/admin/roles',
      name: 'admin-roles',
      component: () => import('../views/admin/AdminRolesView.vue'),
      meta: { permission: 'role:view', admin: true },
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
})

router.beforeEach(async (to) => {
  const authed = Boolean(getToken())

  if (!to.meta.public && !authed) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'login' && authed) {
    return { name: 'dashboard' }
  }
  if (to.meta.public) {
    return true
  }

  const auth = useAuthStore()
  if (!auth.user) {
    try {
      await auth.loadUser()
    } catch {
      auth.logout()
      return { name: 'login' }
    }
  }

  const permission = to.meta.permission as string | undefined
  if (to.meta.admin && !auth.isAdmin) {
    return { name: 'dashboard' }
  }
  if (permission && !auth.hasPermission(permission)) {
    return { name: 'dashboard' }
  }
  return true
})

export default router
