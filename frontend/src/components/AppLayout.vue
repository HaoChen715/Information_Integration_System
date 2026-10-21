<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'
import UserAvatar from './UserAvatar.vue'

const props = withDefaults(defineProps<{ wide?: boolean }>(), { wide: false })

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const mainClass = computed(() =>
  props.wide ? 'mx-auto max-w-[1800px] px-4 py-6' : 'mx-auto max-w-6xl px-6 py-8',
)

const showBack = computed(() => route.path !== '/')

function backFallback(path: string): string {
  if (path.startsWith('/department/')) return '/department'
  if (path === '/monitor') return '/department'
  return '/'
}

function goBack() {
  if (window.history.length > 1) router.back()
  else router.replace(backFallback(route.path))
}

const navItems = computed(() => {
  const items: { to: string; label: string }[] = [
    { to: '/', label: '主页' },
    { to: '/department', label: '部门' },
  ]
  if (auth.hasPermission('record:view')) items.push({ to: '/records', label: '资料' })
  if (auth.canManageUsers) items.push({ to: '/admin/users', label: '用户管理' })
  if (auth.isAdmin) {
    items.push({ to: '/admin/roles', label: '角色管理' })
    items.push({ to: '/admin/departments', label: '部门管理' })
    items.push({ to: '/admin/baserow', label: '数据源' })
  }
  return items
})

function handleLogout() {
  auth.logout()
  router.replace('/login')
}
</script>

<template>
  <div class="min-h-screen bg-slate-100 pt-[60px]">
    <header class="fixed inset-x-0 top-0 z-50 border-b border-slate-200 bg-white/95 backdrop-blur">
      <div class="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
        <div class="flex items-center gap-6">
          <button
            v-if="showBack"
            class="flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1.5 text-sm text-slate-600 transition hover:bg-slate-50"
            @click="goBack"
          >
            ← 返回
          </button>
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
          <div class="flex items-center gap-3">
            <UserAvatar
              :src="auth.user?.avatar_url"
              :name="auth.user?.full_name"
              :username="auth.user?.username"
              :size="36"
            />
            <div class="text-right">
              <p class="text-sm font-medium text-slate-700">{{ auth.displayName }}</p>
              <p class="text-xs text-slate-400">
                {{ auth.isSuperuser ? '超级管理员' : auth.isAdmin ? '管理员' : '用户' }} ·
                {{ auth.user?.auth_source === 'ad' ? 'AD 域' : auth.user?.auth_source === 'oidc' ? '统一认证' : '本地' }}
              </p>
            </div>
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

    <main :class="mainClass">
      <slot />
    </main>
  </div>
</template>
