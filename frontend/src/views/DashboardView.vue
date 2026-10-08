<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()

onMounted(() => {
  if (!auth.user) {
    auth.loadUser().catch(() => {
      auth.logout()
      router.replace('/login')
    })
  }
})

function handleLogout() {
  auth.logout()
  router.replace('/login')
}
</script>

<template>
  <div class="min-h-screen bg-slate-100">
    <header class="border-b border-slate-200 bg-white">
      <div class="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <div class="flex items-center gap-3">
          <div
            class="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-500 font-bold text-white"
          >
            II
          </div>
          <span class="font-semibold text-slate-800">信息集成管理系统</span>
        </div>

        <div class="flex items-center gap-4">
          <div class="text-right">
            <p class="text-sm font-medium text-slate-700">{{ auth.displayName }}</p>
            <p class="text-xs text-slate-400">
              {{ auth.user?.is_superuser ? '管理员' : '普通用户' }}
            </p>
          </div>
          <button
            class="rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-600 transition hover:bg-slate-50"
            @click="handleLogout"
          >
            退出登录
          </button>
        </div>
      </div>
    </header>

    <main class="mx-auto max-w-6xl px-6 py-10">
      <h1 class="text-2xl font-bold text-slate-800">
        你好,{{ auth.displayName }} 👋
      </h1>
      <p class="mt-1 text-sm text-slate-500">登录成功,这里是系统主页占位,后续接入业务模块。</p>

      <div class="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <div class="rounded-2xl border border-slate-200 bg-white p-5">
          <p class="text-xs font-medium uppercase tracking-wide text-slate-400">用户名</p>
          <p class="mt-2 text-lg font-semibold text-slate-800">{{ auth.user?.username }}</p>
        </div>
        <div class="rounded-2xl border border-slate-200 bg-white p-5">
          <p class="text-xs font-medium uppercase tracking-wide text-slate-400">邮箱</p>
          <p class="mt-2 text-lg font-semibold text-slate-800">
            {{ auth.user?.email || '—' }}
          </p>
        </div>
        <div class="rounded-2xl border border-slate-200 bg-white p-5">
          <p class="text-xs font-medium uppercase tracking-wide text-slate-400">最近登录</p>
          <p class="mt-2 text-lg font-semibold text-slate-800">
            {{ auth.user?.last_login_at ? new Date(auth.user.last_login_at).toLocaleString() : '—' }}
          </p>
        </div>
      </div>
    </main>
  </div>
</template>
