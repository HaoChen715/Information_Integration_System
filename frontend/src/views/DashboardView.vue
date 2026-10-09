<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import AppLayout from '../components/AppLayout.vue'
import UserAvatar from '../components/UserAvatar.vue'
import { fetchDepartmentMembers, fetchOnlineUsers, fetchStats } from '../api/admin'
import type { OnlineUser, UserStats } from '../api/admin'
import { removeAvatar, uploadAvatar } from '../api/auth'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()

const stats = ref<UserStats | null>(null)
const onlineUsers = ref<OnlineUser[]>([])
const showOnline = ref(false)
const loadingOnline = ref(false)
const deptMemberCount = ref(0)
const fileInput = ref<HTMLInputElement | null>(null)
const avatarMsg = ref('')
const uploading = ref(false)

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
      /* 忽略 */
    }
  }
  if (auth.canManageUsers || auth.user?.department) {
    try {
      deptMemberCount.value = (await fetchDepartmentMembers()).length
    } catch {
      /* 忽略 */
    }
  }
})

const permissionCount = computed(() => Object.keys(auth.permissions).length)

function relative(iso: string | null): string {
  if (!iso) return '—'
  const diff = Date.now() - new Date(iso).getTime()
  const min = Math.floor(diff / 60000)
  if (min < 1) return '刚刚'
  if (min < 60) return `${min} 分钟前`
  const h = Math.floor(min / 60)
  if (h < 24) return `${h} 小时前`
  return `${Math.floor(h / 24)} 天前`
}

async function openOnline() {
  showOnline.value = true
  loadingOnline.value = true
  try {
    onlineUsers.value = await fetchOnlineUsers()
  } catch {
    onlineUsers.value = []
  } finally {
    loadingOnline.value = false
  }
}

function pickAvatar() {
  fileInput.value?.click()
}

async function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  avatarMsg.value = ''
  uploading.value = true
  try {
    await uploadAvatar(file)
    await auth.loadUser()
    avatarMsg.value = '头像已更新'
  } catch (err) {
    avatarMsg.value =
      (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '上传失败'
  } finally {
    uploading.value = false
  }
}

async function removeAv() {
  uploading.value = true
  avatarMsg.value = ''
  try {
    await removeAvatar()
    await auth.loadUser()
    avatarMsg.value = '头像已移除'
  } catch {
    avatarMsg.value = '操作失败'
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <AppLayout>
    <h1 class="text-2xl font-bold text-slate-800">你好,{{ auth.displayName }} 👋</h1>
    <p class="mt-1 text-sm text-slate-500">登录成功,这里是系统主页。</p>

    <div
      class="mt-6 flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-5 sm:flex-row sm:items-center"
    >
      <UserAvatar
        :src="auth.user?.avatar_url"
        :name="auth.user?.full_name"
        :username="auth.user?.username"
        :size="72"
      />
      <div class="flex-1">
        <p class="text-lg font-semibold text-slate-800">{{ auth.displayName }}</p>
        <p class="text-sm text-slate-500">
          {{ auth.user?.department || '未设置部门' }} · @{{ auth.user?.username }}
        </p>
        <p v-if="avatarMsg" class="mt-1 text-xs text-slate-400">{{ avatarMsg }}</p>
      </div>
      <div class="flex gap-2">
        <button
          class="rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-600 transition hover:bg-slate-50 disabled:opacity-50"
          :disabled="uploading"
          @click="pickAvatar"
        >
          上传头像
        </button>
        <button
          v-if="auth.user?.avatar_url"
          class="rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-red-500 transition hover:bg-red-50 disabled:opacity-50"
          :disabled="uploading"
          @click="removeAv"
        >
          移除
        </button>
        <input
          ref="fileInput"
          type="file"
          accept="image/png,image/jpeg,image/webp"
          class="hidden"
          @change="onFileChange"
        />
      </div>
    </div>

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
          <template v-if="auth.user?.role_names.length">
            <span
              v-for="role in auth.user.role_names"
              :key="role"
              class="rounded-md bg-indigo-50 px-2 py-0.5 text-sm font-medium text-indigo-600"
            >
              {{ role }}
            </span>
          </template>
          <span v-else-if="auth.isSuperuser" class="rounded-md bg-amber-50 px-2 py-0.5 text-sm font-medium text-amber-600">
            超级管理员
          </span>
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
        <button
          class="bg-white p-6 text-left transition hover:bg-emerald-50/50"
          @click="openOnline"
        >
          <p class="text-xs uppercase tracking-wide text-slate-400">当前在线</p>
          <p class="mt-2 flex items-center gap-2 text-3xl font-bold text-emerald-600">
            <span class="relative flex h-3 w-3">
              <span
                class="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"
              />
              <span class="relative inline-flex h-3 w-3 rounded-full bg-emerald-500" />
            </span>
            {{ stats?.online_users ?? '—' }}
            <span class="ml-1 text-xs font-normal text-slate-400">点击查看</span>
          </p>
        </button>
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

    <div
      v-else-if="auth.canManageUsers"
      class="mt-6 flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-5 sm:flex-row sm:items-center sm:justify-between"
    >
      <div>
        <p class="font-semibold text-slate-800">本部门员工管理</p>
        <p class="mt-0.5 text-xs text-slate-400">
          {{ auth.user?.department || '未设置部门' }} · 共 {{ deptMemberCount }} 人
        </p>
      </div>
      <div class="flex gap-2">
        <RouterLink
          to="/department"
          class="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600 transition hover:bg-slate-50"
        >
          部门空间
        </RouterLink>
        <RouterLink
          to="/admin/users"
          class="rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-600"
        >
          用户管理 →
        </RouterLink>
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
          {{ auth.user?.permission_labels?.[code] || code }}
          <span class="ml-1 text-slate-400">{{
            scope === 'all' ? '全部' : scope === 'dept' ? '本部门' : '仅本人'
          }}</span>
        </span>
        <span v-if="!permissionCount" class="text-sm text-slate-400">暂无权限</span>
      </div>
    </div>

    <!-- 在线用户弹框 -->
    <div
      v-if="showOnline"
      class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4"
      @click.self="showOnline = false"
    >
      <div class="w-full max-w-lg overflow-hidden rounded-2xl bg-white shadow-xl">
        <div class="flex items-center justify-between border-b border-slate-100 px-6 py-4">
          <div>
            <h2 class="font-bold text-slate-800">当前在线用户</h2>
            <p class="mt-0.5 text-xs text-slate-400">共 {{ onlineUsers.length }} 人</p>
          </div>
          <button class="text-slate-400 hover:text-slate-600" @click="showOnline = false">✕</button>
        </div>

        <div class="max-h-[60vh] overflow-y-auto">
          <div v-if="loadingOnline" class="px-6 py-10 text-center text-sm text-slate-400">
            加载中...
          </div>
          <div v-else-if="!onlineUsers.length" class="px-6 py-10 text-center text-sm text-slate-400">
            当前无在线用户
          </div>
          <ul v-else class="divide-y divide-slate-100">
            <li
              v-for="u in onlineUsers"
              :key="u.id"
              class="flex items-center gap-3 px-6 py-3"
            >
              <UserAvatar :src="u.avatar_url" :name="u.full_name" :username="u.username" :size="40" />
              <div class="min-w-0 flex-1">
                <p class="truncate text-sm font-medium text-slate-800">
                  {{ u.full_name || u.username }}
                  <span class="ml-1 text-xs font-normal text-slate-400">@{{ u.username }}</span>
                </p>
                <p class="truncate text-xs text-slate-500">
                  {{ u.department || '未设置部门' }} ·
                  {{ u.auth_source === 'ad' ? 'AD 域' : u.auth_source === 'oidc' ? '统一认证' : '本地' }}
                </p>
              </div>
              <span class="shrink-0 text-xs text-slate-400">{{ relative(u.last_seen_at) }}</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </AppLayout>
</template>
