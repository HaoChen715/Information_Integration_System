<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import AppLayout from '../components/AppLayout.vue'
import { fetchStats } from '../api/admin'
import type { UserStats } from '../api/admin'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()

const stats = ref<UserStats | null>(null)

onMounted(async () => {
  if (!auth.user) {
    try {
      await auth.loadUser()
    } catch {
      auth.logout()
      router.replace('/login')
      return
    }
  }
  if (auth.isAdmin) {
    try {
      stats.value = await fetchStats()
    } catch {
      /* 无权限或失败则忽略 */
    }
  }
})

const permissionCount = computed(() => Object.keys(auth.permissions).length)
</script>

<template>
  <AppLayout>
    <h1 class="text-2xl font-bold text-slate-800">你好,{{ auth.displayName }} 👋</h1>
    <p class="mt-1 text-sm text-slate-500">登录成功,这里是系统主页。</p>

    <div class="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <div class="rounded-2xl border border-slate-200 bg-white p-5">
        <p class="text-xs font-medium uppercase tracking-wide text-slate-400">用户名</p>
        <p class="mt-2 text-lg font-semibold text-slate-800">{{ auth.user?.username }}</p>
      </div>
      <div class="rounded-2xl border border-slate-200 bg-white p-5">
        <p class="text-xs font-medium uppercase tracking-wide text-slate-400">部门</p>
        <p class="mt-2 text-lg font-semibold text-slate-800">{{ auth.user?.department || '—' }}</p>
      </div>
      <div class="rounded-2xl border border-slate-200 bg-white p-5">
        <p class="text-xs font-medium uppercase tracking-wide text-slate-400">角色</p>
        <div class="mt-2 flex flex-wrap gap-1.5">
          <template v-if="auth.user?.roles.length">
            <span
              v-for="role in auth.user.roles"
              :key="role"
              class="rounded-md bg-indigo-50 px-2 py-0.5 text-sm font-medium text-indigo-600"
            >
              {{ role }}
            </span>
          </template>
          <span v-else class="text-lg font-semibold text-slate-800">—</span>
        </div>
      </div>
      <div class="rounded-2xl border border-slate-200 bg-white p-5">
        <p class="text-xs font-medium uppercase tracking-wide text-slate-400">我的权限</p>
        <p class="mt-2 text-lg font-semibold text-slate-800">{{ permissionCount }}</p>
      </div>
    </div>

    <!-- 管理员:用户概览 -->
    <div
      v-if="auth.isAdmin"
      class="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white"
    >
      <div class="flex items-center justify-between border-b border-slate-100 px-6 py-4">
        <div>
          <p class="font-semibold text-slate-800">用户概览</p>
          <p class="mt-0.5 text-xs text-slate-400">
            在线 = 最近 {{ stats?.online_window_minutes ?? 15 }} 分钟内有操作
          </p>
        </div>
        <RouterLink
          to="/admin/users"
          class="rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-600"
        >
          查看用户列表 →
        </RouterLink>
      </div>

      <div class="grid gap-px bg-slate-100 sm:grid-cols-3">
        <div class="bg-white p-6">
          <p class="text-xs uppercase tracking-wide text-slate-400">已注册用户</p>
          <p class="mt-2 text-3xl font-bold text-slate-800">{{ stats?.total_users ?? '—' }}</p>
        </div>
        <div class="bg-white p-6">
          <p class="text-xs uppercase tracking-wide text-slate-400">当前在线</p>
          <p class="mt-2 flex items-center gap-2 text-3xl font-bold text-emerald-600">
            <span class="relative flex h-3 w-3">
              <span class="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
              <span class="relative inline-flex h-3 w-3 rounded-full bg-emerald-500" />
            </span>
            {{ stats?.online_users ?? '—' }}
          </p>
        </div>
        <div class="bg-white p-6">
          <p class="text-xs uppercase tracking-wide text-slate-400">账号来源</p>
          <div class="mt-2 flex flex-wrap gap-3 text-sm text-slate-600">
            <span>本地 {{ stats?.by_source?.local ?? 0 }}</span>
            <span>AD 域 {{ stats?.by_source?.ad ?? 0 }}</span>
            <span>统一认证 {{ stats?.by_source?.oidc ?? 0 }}</span>
          </div>
        </div>
      </div>
    </div>

    <div class="mt-6 rounded-2xl border border-slate-200 bg-white p-5">
      <p class="text-sm font-semibold text-slate-700">我的权限</p>
      <div class="mt-3 flex flex-wrap gap-2">
        <span
          v-for="(scope, code) in auth.permissions"
          :key="code"
          class="rounded-md border border-slate-200 px-2 py-0.5 text-xs text-slate-600"
        >
          {{ code }}
          <span class="ml-1 text-slate-400">{{
            scope === 'all' ? '全部' : scope === 'dept' ? '本部门' : '仅本人'
          }}</span>
        </span>
        <span v-if="!permissionCount" class="text-sm text-slate-400">暂无权限</span>
      </div>
    </div>
  </AppLayout>
</template>
