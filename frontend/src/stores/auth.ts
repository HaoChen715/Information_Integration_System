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

  function logout(): void {
    clearToken()
    token.value = null
    user.value = null
  }

  return { user, token, loading, isAuthenticated, displayName, login, loadUser, logout }
})
