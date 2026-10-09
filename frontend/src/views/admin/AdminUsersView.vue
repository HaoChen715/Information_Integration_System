<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import AppLayout from '../../components/AppLayout.vue'
import PermissionPicker from '../../components/PermissionPicker.vue'
import UserAvatar from '../../components/UserAvatar.vue'
import * as adminApi from '../../api/admin'
import type { AdminUser, Department, PermissionGroup, Role, UserStats } from '../../api/admin'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()

const users = ref<AdminUser[]>([])
const roles = ref<Role[]>([])
const groups = ref<PermissionGroup[]>([])
const departments = ref<Department[]>([])
const stats = ref<UserStats | null>(null)

const editing = ref<AdminUser | null>(null)
const form = ref({
  full_name: '',
  department: '',
  is_active: true,
  is_superuser: false,
  roles: [] as string[],
  permissions: {} as Record<string, string>,
})
const saving = ref(false)
const message = ref('')

const canEditProfile = computed(() => auth.isAdmin)
const disabledResources = computed(() => (auth.isAdmin ? [] : ['user', 'role']))

async function loadAll() {
  const tasks: Promise<unknown>[] = [
    adminApi.fetchAdminUsers().then((v) => (users.value = v)),
    adminApi.fetchRoles().then((v) => (roles.value = v)),
    adminApi.fetchPermissions().then((v) => (groups.value = v)),
    adminApi.fetchDepartments().then((v) => (departments.value = v)),
  ]
  if (auth.isAdmin) {
    tasks.push(adminApi.fetchStats().then((v) => (stats.value = v)).catch(() => {}))
  }
  await Promise.all(tasks)
}

function openEdit(user: AdminUser) {
  editing.value = user
  message.value = ''
  form.value = {
    full_name: user.full_name ?? '',
    department: user.department ?? '',
    is_active: user.is_active,
    is_superuser: user.is_superuser,
    roles: [...user.roles],
    permissions: Object.fromEntries(
      user.direct_permissions.map((g) => [g.code, g.data_scope]),
    ),
  }
}

function closeEdit() {
  editing.value = null
}

function toggleRole(code: string, checked: boolean) {
  const set = new Set(form.value.roles)
  if (checked) set.add(code)
  else set.delete(code)
  form.value.roles = [...set]
}

function roleDisabled(role: Role) {
  if (role.is_admin) return !auth.isSuperuser
  if (role.is_department_manager) return !auth.isAdmin
  return false
}

async function save() {
  const user = editing.value
  if (!user) return
  saving.value = true
  message.value = ''
  try {
    if (auth.isAdmin) {
      await adminApi.updateUser(user.id, {
        full_name: form.value.full_name,
        department: form.value.department || null,
        is_active: form.value.is_active,
      })
    }
    await adminApi.assignRoles(user.id, form.value.roles)
    await adminApi.setUserPermissions(
      user.id,
      Object.entries(form.value.permissions).map(([code, data_scope]) => ({ code, data_scope })),
    )
    if (auth.isSuperuser && form.value.is_superuser !== user.is_superuser) {
      await adminApi.setSuperuser(user.id, form.value.is_superuser)
    }
    await loadAll()
    editing.value = users.value.find((u) => u.id === user.id) ?? null
    message.value = '已保存'
  } catch (err: unknown) {
    message.value =
      (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '保存失败'
  } finally {
    saving.value = false
  }
}

onMounted(loadAll)
</script>

<template>
  <AppLayout>
    <h1 class="text-2xl font-bold text-slate-800">用户管理</h1>
    <p class="mt-1 text-sm text-slate-500">
      {{ auth.isAdmin ? '为用户分配角色与页面权限,并设置数据范围。' : '管理本部门员工的角色与权限。' }}
    </p>

    <div v-if="auth.isAdmin" class="mt-4 flex flex-wrap gap-4 text-sm">
      <span class="rounded-lg bg-white px-3 py-1.5 text-slate-600 ring-1 ring-slate-200">
        已注册 <b class="text-slate-800">{{ stats?.total_users ?? '—' }}</b> 人
      </span>
      <span class="rounded-lg bg-white px-3 py-1.5 text-slate-600 ring-1 ring-slate-200">
        当前在线 <b class="text-emerald-600">{{ stats?.online_users ?? '—' }}</b> 人
      </span>
    </div>

    <div class="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white">
      <table class="w-full text-sm">
        <thead class="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-400">
          <tr>
            <th class="px-5 py-3">账号</th>
            <th class="px-5 py-3">姓名</th>
            <th class="px-5 py-3">部门</th>
            <th class="px-5 py-3">来源</th>
            <th class="px-5 py-3">角色</th>
            <th class="px-5 py-3">权限数</th>
            <th class="px-5 py-3">操作</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          <tr v-for="u in users" :key="u.id">
            <td class="px-5 py-3 font-medium text-slate-700">
              <div class="flex items-center gap-3">
                <UserAvatar :src="u.avatar_url" :name="u.full_name" :username="u.username" :size="34" />
                <span>
                  {{ u.username }}
                  <span v-if="u.is_superuser" class="ml-1 rounded bg-amber-100 px-1.5 py-0.5 text-xs text-amber-700">超管</span>
                </span>
              </div>
            </td>
            <td class="px-5 py-3 text-slate-500">{{ u.full_name || '—' }}</td>
            <td class="px-5 py-3 text-slate-500">{{ u.department || '—' }}</td>
            <td class="px-5 py-3 text-slate-500">{{ u.auth_source }}</td>
            <td class="px-5 py-3">
              <span
                v-for="r in u.roles"
                :key="r"
                class="mr-1 rounded bg-indigo-50 px-1.5 py-0.5 text-xs text-indigo-600"
              >{{ r }}</span>
              <span v-if="!u.roles.length" class="text-slate-400">—</span>
            </td>
            <td class="px-5 py-3 text-slate-500">{{ Object.keys(u.permissions).length }}</td>
            <td class="px-5 py-3">
              <button class="text-indigo-600 hover:underline" @click="openEdit(u)">编辑</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 编辑弹层 -->
    <div
      v-if="editing"
      class="fixed inset-0 z-50 flex justify-end bg-slate-900/40"
      @click.self="closeEdit"
    >
      <div class="h-full w-full max-w-xl overflow-y-auto bg-white p-6 shadow-xl">
        <div class="flex items-center justify-between">
          <h2 class="text-lg font-bold text-slate-800">编辑用户:{{ editing.username }}</h2>
          <button class="text-slate-400 hover:text-slate-600" @click="closeEdit">✕</button>
        </div>

        <div class="mt-5 space-y-4">
          <div class="grid grid-cols-2 gap-3">
            <label class="block">
              <span class="mb-1 block text-sm text-slate-600">姓名</span>
              <input
                v-model="form.full_name"
                :disabled="!canEditProfile"
                class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm disabled:bg-slate-50"
              />
            </label>
            <label class="block">
              <span class="mb-1 block text-sm text-slate-600">部门</span>
              <select
                v-model="form.department"
                :disabled="!canEditProfile"
                class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm disabled:bg-slate-50"
              >
                <option value="">未设置</option>
                <option v-for="d in departments" :key="d.id" :value="d.name">{{ d.name }}</option>
              </select>
            </label>
          </div>

          <div class="flex items-center gap-4">
            <label
              class="flex items-center gap-2 text-sm"
              :class="canEditProfile ? 'text-slate-600' : 'text-slate-300'"
            >
              <input
                v-model="form.is_active"
                type="checkbox"
                class="h-4 w-4 accent-indigo-500"
                :disabled="!canEditProfile"
              />启用账号
            </label>
            <label
              v-if="auth.isSuperuser"
              class="flex items-center gap-2 text-sm text-slate-600"
            >
              <input v-model="form.is_superuser" type="checkbox" class="h-4 w-4 accent-amber-500" />超级管理员
            </label>
          </div>

          <div>
            <p class="mb-2 text-sm font-semibold text-slate-700">角色</p>
            <div class="flex flex-wrap gap-3">
              <label
                v-for="role in roles"
                :key="role.id"
                class="flex items-center gap-2 text-sm"
                :class="roleDisabled(role) ? 'text-slate-300' : 'text-slate-600'"
              >
                <input
                  type="checkbox"
                  class="h-4 w-4 accent-indigo-500"
                  :disabled="roleDisabled(role)"
                  :checked="form.roles.includes(role.code)"
                  @change="toggleRole(role.code, ($event.target as HTMLInputElement).checked)"
                />
                {{ role.name }}
                <span v-if="role.is_admin" class="rounded bg-amber-100 px-1 text-xs text-amber-700">管理</span>
                <span v-else-if="role.is_department_manager" class="rounded bg-sky-100 px-1 text-xs text-sky-700">主管</span>
              </label>
            </div>
          </div>

          <div>
            <p class="mb-2 text-sm font-semibold text-slate-700">页面权限(直接授权)</p>
            <PermissionPicker
              v-model="form.permissions"
              :groups="groups"
              :disabled-resources="disabledResources"
            />
          </div>

          <div class="flex items-center gap-3 pt-2">
            <button
              class="rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-600 disabled:opacity-50"
              :disabled="saving"
              @click="save"
            >
              {{ saving ? '保存中...' : '保存' }}
            </button>
            <span v-if="message" class="text-sm text-slate-500">{{ message }}</span>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>
