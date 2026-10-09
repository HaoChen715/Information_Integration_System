import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import * as authApi from '../api/auth'
import { clearToken, getToken, setToken } from '../api/client'
import type { CurrentUser } from '../api/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<CurrentUser | null>(null)
  const token = ref<string | null>(getToken())
  const loading = ref(false)

  const isAuthenticated = computed(() => Boolean(token.value))
  const displayName = computed(() => user.value?.full_name || user.value?.username || '')
  const permissions = computed<Record<string, string>>(() => user.value?.permissions ?? {})
  const isAdmin = computed(() => Boolean(user.value?.is_admin || user.value?.is_superuser))
  const isSuperuser = computed(() => Boolean(user.value?.is_superuser))
  const manageScope = computed(() => user.value?.manage_scope ?? null)
  const canManageUsers = computed(() => Boolean(manageScope.value))

  function hasPermission(code: string): boolean {
    if (user.value?.is_superuser) return true
    return code in (user.value?.permissions ?? {})
  }

  function scopeOf(code: string): string | null {
    return user.value?.permissions?.[code] ?? null
  }

  async function login(username: string, password: string): Promise<void> {
    const data = await authApi.login(username, password)
    setToken(data.access_token)
    token.value = data.access_token
    await loadUser()
  }

  async function loadUser(): Promise<void> {
    if (!token.value) return
    user.value = await authApi.fetchCurrentUser()
  }

  async function acceptToken(newToken: string): Promise<void> {
    setToken(newToken)
    token.value = newToken
    await loadUser()
  }

  function logout(): void {
    clearToken()
    token.value = null
    user.value = null
  }

  return {
    user,
    token,
    loading,
    isAuthenticated,
    displayName,
    permissions,
    isAdmin,
    isSuperuser,
    manageScope,
    canManageUsers,
    hasPermission,
    scopeOf,
    login,
    loadUser,
    acceptToken,
    logout,
  }
})
