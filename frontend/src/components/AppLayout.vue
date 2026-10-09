<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()

const navItems = computed(() =>
  [
    { to: '/', label: '主页', perm: '' },
    { to: '/records', label: '资料', perm: 'record:view' },
    { to: '/admin/users', label: '用户管理', perm: 'user:view' },
    { to: '/admin/roles', label: '角色管理', perm: 'role:view' },
  ].filter((item) => !item.perm || auth.hasPermission(item.perm)),
)

function handleLogout() {
  auth.logout()
  router.replace('/login')
}
</script>

<template>
  <div class="min-h-screen bg-slate-100">
    <header class="border-b border-slate-200 bg-white">
      <div class="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
        <div class="flex items-center gap-6">
          <div class="flex items-center gap-2">
            <div
              class="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-500 font-bold text-white"
            >
              II
            </div>
            <span class="font-semibold text-slate-800">信息集成管理系统</span>
          </div>
          <nav class="hidden items-center gap-1 md:flex">
            <RouterLink
              v-for="item in navItems"
              :key="item.to"
              :to="item.to"
              class="rounded-lg px-3 py-1.5 text-sm text-slate-600 transition hover:bg-slate-100"
              active-class="!bg-indigo-50 !text-indigo-600 font-medium"
            >
              {{ item.label }}
            </RouterLink>
          </nav>
        </div>

        <div class="flex items-center gap-4">
          <div class="text-right">
            <p class="text-sm font-medium text-slate-700">{{ auth.displayName }}</p>
            <p class="text-xs text-slate-400">
              {{ auth.isSuperuser ? '超级管理员' : auth.isAdmin ? '管理员' : '用户' }} ·
              {{ auth.user?.auth_source === 'ad' ? 'AD 域' : auth.user?.auth_source === 'oidc' ? '统一认证' : '本地' }}
            </p>
          </div>
          <button
            class="rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-600 transition hover:bg-slate-50"
            @click="handleLogout"
          >
            退出
          </button>
        </div>
      </div>
    </header>

    <main class="mx-auto max-w-6xl px-6 py-8">
      <slot />
    </main>
  </div>
</template>
