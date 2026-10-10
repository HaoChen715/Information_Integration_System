<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import AppLayout from '../components/AppLayout.vue'
import UserAvatar from '../components/UserAvatar.vue'
import {
  fetchAdminUsers,
  fetchDepartments,
  fetchDepartmentMembers,
} from '../api/admin'
import type { AdminUser, Department, DepartmentMember } from '../api/admin'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()

const departments = ref<Department[]>([])
const allUsers = ref<AdminUser[]>([])
const members = ref<DepartmentMember[]>([])
const selectedDept = ref('')

const cards = [
  { title: '数据看板', desc: '部门数据统计与可视化' },
  { title: '任务中心', desc: '待办与任务流转' },
  { title: '公告通知', desc: '部门公告与消息' },
  { title: '文档库', desc: '共享文档与资料' },
]

const adminMembers = computed(() =>
  allUsers.value.filter((u) => (u.department ?? '') === selectedDept.value),
)

function deptCount(name: string): number {
  return allUsers.value.filter((u) => (u.department ?? '') === name).length
}

onMounted(async () => {
  if (!auth.user) {
    try {
      await auth.loadUser()
    } catch {
      return
    }
  }
  if (auth.isAdmin) {
    departments.value = await fetchDepartments()
    allUsers.value = await fetchAdminUsers()
    if (departments.value.length) selectedDept.value = departments.value[0].name
  } else {
    try {
      members.value = await fetchDepartmentMembers()
    } catch {
      members.value = []
    }
  }
})
</script>

<template>
  <AppLayout>
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-slate-800">部门空间</h1>
        <p class="mt-1 text-sm text-slate-500">
          <template v-if="auth.isAdmin">全部部门 · 共 {{ departments.length }} 个</template>
          <template v-else>{{ auth.user?.department || '未设置部门' }} · 共 {{ members.length }} 人</template>
        </p>
      </div>
      <RouterLink
        v-if="auth.canManageUsers"
        to="/admin/users"
        class="rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-600"
      >
        用户管理 →
      </RouterLink>
    </div>

    <div class="mt-6 grid gap-6 lg:grid-cols-3">
      <!-- 左侧 -->
      <div class="rounded-2xl border border-slate-200 bg-white p-4 lg:col-span-1">
        <!-- 管理员:全部部门 -->
        <template v-if="auth.isAdmin">
          <p class="mb-2 px-2 text-sm font-semibold text-slate-700">全部部门</p>
          <ul class="space-y-0.5">
            <li v-for="d in departments" :key="d.id">
              <button
                class="flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm transition"
                :class="selectedDept === d.name ? 'bg-indigo-50 text-indigo-700' : 'text-slate-600 hover:bg-slate-50'"
                @click="selectedDept = d.name"
              >
                <span class="font-medium">{{ d.name }}</span>
                <span class="text-xs text-slate-400">{{ deptCount(d.name) }} 人</span>
              </button>
            </li>
            <li v-if="!departments.length" class="px-2 py-6 text-center text-sm text-slate-400">
              暂无部门
            </li>
          </ul>
        </template>

        <!-- 普通用户/主管:本部门员工 -->
        <template v-else>
          <p class="mb-2 px-2 text-sm font-semibold text-slate-700">部门员工</p>
          <ul class="max-h-[70vh] space-y-0.5 overflow-y-auto">
            <li
              v-for="m in members"
              :key="m.id"
              class="flex items-center gap-3 rounded-lg px-2 py-2 transition hover:bg-slate-50"
            >
              <UserAvatar :src="m.avatar_url" :name="m.full_name" :username="m.username" :size="38" />
              <div class="min-w-0 flex-1">
                <p class="truncate text-sm font-medium text-slate-800">
                  {{ m.full_name || m.username }}
                  <span v-if="!m.is_active" class="ml-1 rounded bg-slate-100 px-1 text-xs text-slate-400">停用</span>
                </p>
                <p class="truncate text-xs text-slate-400">
                  {{ m.role_names.length ? m.role_names.join('、') : '@' + m.username }}
                </p>
              </div>
            </li>
            <li v-if="!members.length" class="px-2 py-8 text-center text-sm text-slate-400">暂无员工</li>
          </ul>
        </template>
      </div>

      <!-- 右侧 -->
      <div class="space-y-6 lg:col-span-2">
        <!-- 管理员:选中部门的成员 -->
        <div v-if="auth.isAdmin" class="rounded-2xl border border-slate-200 bg-white p-5">
          <div class="flex items-center justify-between">
            <p class="font-semibold text-slate-800">
              {{ selectedDept || '请选择部门' }}
              <span class="ml-2 text-sm font-normal text-slate-400">{{ adminMembers.length }} 人</span>
            </p>
          </div>
          <div class="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            <div
              v-for="m in adminMembers"
              :key="m.id"
              class="flex items-center gap-3 rounded-xl border border-slate-100 p-3 transition hover:bg-slate-50"
            >
              <UserAvatar :src="m.avatar_url" :name="m.full_name" :username="m.username" :size="40" />
              <div class="min-w-0">
                <p class="truncate text-sm font-medium text-slate-800">
                  {{ m.full_name || m.username }}
                  <span v-if="!m.is_active" class="ml-1 rounded bg-slate-100 px-1 text-xs text-slate-400">停用</span>
                </p>
                <p class="truncate text-xs text-slate-400">
                  {{ m.role_names.length ? m.role_names.join('、') : '@' + m.username }}
                </p>
              </div>
            </div>
            <p v-if="selectedDept && !adminMembers.length" class="col-span-full py-6 text-center text-sm text-slate-400">
              该部门暂无成员
            </p>
          </div>
        </div>

        <!-- 功能入口玻璃卡片(占位) -->
        <div
          class="relative overflow-hidden rounded-2xl bg-gradient-to-br from-indigo-600 via-violet-600 to-cyan-500 p-6"
        >
          <div
            class="pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full bg-white/10 blur-2xl"
          />
          <div
            class="pointer-events-none absolute -bottom-20 -left-10 h-56 w-56 rounded-full bg-cyan-300/20 blur-2xl"
          />
          <p class="relative font-semibold text-white/90">功能入口</p>
          <p class="relative mt-0.5 text-xs text-white/60">后续将作为各功能页面的跳转入口</p>
          <div class="relative mt-5 grid gap-4 sm:grid-cols-2">
            <div
              v-for="card in cards"
              :key="card.title"
              class="group rounded-2xl border border-white/20 bg-white/10 p-5 backdrop-blur-md transition hover:bg-white/20"
            >
              <p class="font-semibold text-white">{{ card.title }}</p>
              <p class="mt-1 text-xs text-white/70">{{ card.desc }}</p>
              <span class="mt-4 inline-block text-xs text-white/50 group-hover:text-white/80">
                敬请期待 →
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>
