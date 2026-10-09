<script setup lang="ts">
import { onMounted, ref } from 'vue'

import AppLayout from '../../components/AppLayout.vue'
import PermissionPicker from '../../components/PermissionPicker.vue'
import * as adminApi from '../../api/admin'
import type { PermissionGroup, Role } from '../../api/admin'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()

const roles = ref<Role[]>([])
const groups = ref<PermissionGroup[]>([])
const saving = ref(false)
const message = ref('')

const form = ref({
  id: null as number | null,
  code: '',
  name: '',
  description: '',
  is_admin: false,
  is_department_manager: false,
  permissions: {} as Record<string, string>,
})
const showForm = ref(false)

async function loadAll() {
  const [r, g] = await Promise.all([adminApi.fetchRoles(), adminApi.fetchPermissions()])
  roles.value = r
  groups.value = g
}

function startCreate() {
  showForm.value = true
  message.value = ''
  form.value = {
    id: null,
    code: '',
    name: '',
    description: '',
    is_admin: false,
    is_department_manager: false,
    permissions: {},
  }
}

function startEdit(role: Role) {
  showForm.value = true
  message.value = ''
  form.value = {
    id: role.id,
    code: role.code,
    name: role.name,
    description: role.description ?? '',
    is_admin: role.is_admin,
    is_department_manager: role.is_department_manager,
    permissions: Object.fromEntries(role.permissions.map((g) => [g.code, g.data_scope])),
  }
}

async function save() {
  saving.value = true
  message.value = ''
  const grants = Object.entries(form.value.permissions).map(([code, data_scope]) => ({
    code,
    data_scope,
  }))
  try {
    if (form.value.id === null) {
      await adminApi.createRole({
        code: form.value.code,
        name: form.value.name,
        description: form.value.description,
        is_admin: form.value.is_admin,
        is_department_manager: form.value.is_department_manager,
        permissions: grants,
      })
    } else {
      await adminApi.updateRole(form.value.id, {
        name: form.value.name,
        description: form.value.description,
        is_admin: form.value.is_admin,
        is_department_manager: form.value.is_department_manager,
        permissions: grants,
      })
    }
    await loadAll()
    showForm.value = false
  } catch (err: unknown) {
    message.value =
      (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '保存失败'
  } finally {
    saving.value = false
  }
}

async function remove(role: Role) {
  if (!confirm(`确认删除角色「${role.name}」?`)) return
  try {
    await adminApi.deleteRole(role.id)
    await loadAll()
  } catch (err: unknown) {
    alert((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '删除失败')
  }
}

onMounted(loadAll)
</script>

<template>
  <AppLayout>
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-slate-800">角色管理</h1>
        <p class="mt-1 text-sm text-slate-500">角色是权限的集合,可分配给用户。</p>
      </div>
      <button
        class="rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-600"
        @click="startCreate"
      >
        新建角色
      </button>
    </div>

    <div class="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white">
      <table class="w-full text-sm">
        <thead class="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-400">
          <tr>
            <th class="px-5 py-3">code</th>
            <th class="px-5 py-3">名称</th>
            <th class="px-5 py-3">说明</th>
            <th class="px-5 py-3">权限数</th>
            <th class="px-5 py-3">操作</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          <tr v-for="role in roles" :key="role.id">
            <td class="px-5 py-3 font-mono text-slate-700">{{ role.code }}</td>
            <td class="px-5 py-3 text-slate-700">
              {{ role.name }}
              <span v-if="role.is_admin" class="ml-1 rounded bg-amber-100 px-1.5 py-0.5 text-xs text-amber-700">管理</span>
              <span v-else-if="role.is_department_manager" class="ml-1 rounded bg-sky-100 px-1.5 py-0.5 text-xs text-sky-700">主管</span>
              <span v-if="role.is_system" class="ml-1 rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-500">内置</span>
            </td>
            <td class="px-5 py-3 text-slate-500">{{ role.description || '—' }}</td>
            <td class="px-5 py-3 text-slate-500">{{ role.permissions.length }}</td>
            <td class="px-5 py-3">
              <button class="mr-3 text-indigo-600 hover:underline" @click="startEdit(role)">编辑</button>
              <button
                v-if="!role.is_system"
                class="text-red-500 hover:underline"
                @click="remove(role)"
              >
                删除
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 表单弹层 -->
    <div
      v-if="showForm"
      class="fixed inset-0 z-50 flex justify-end bg-slate-900/40"
      @click.self="showForm = false"
    >
      <div class="h-full w-full max-w-xl overflow-y-auto bg-white p-6 shadow-xl">
        <h2 class="text-lg font-bold text-slate-800">
          {{ form.id === null ? '新建角色' : '编辑角色' }}
        </h2>

        <div class="mt-5 space-y-4">
          <div class="grid grid-cols-2 gap-3">
            <label class="block">
              <span class="mb-1 block text-sm text-slate-600">code</span>
              <input
                v-model="form.code"
                :disabled="form.id !== null"
                class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm disabled:bg-slate-50"
              />
            </label>
            <label class="block">
              <span class="mb-1 block text-sm text-slate-600">名称</span>
              <input v-model="form.name" class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm" />
            </label>
          </div>

          <label class="block">
            <span class="mb-1 block text-sm text-slate-600">说明</span>
            <input v-model="form.description" class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm" />
          </label>

          <label
            class="flex items-center gap-2 text-sm"
            :class="auth.isSuperuser ? 'text-slate-600' : 'text-slate-300'"
          >
            <input
              v-model="form.is_admin"
              type="checkbox"
              class="h-4 w-4 accent-amber-500"
              :disabled="!auth.isSuperuser"
            />
            管理员角色(仅超级管理员可设置)
          </label>

          <label class="flex items-center gap-2 text-sm text-slate-600">
            <input v-model="form.is_department_manager" type="checkbox" class="h-4 w-4 accent-sky-500" />
            主管角色(可管理本部门员工的角色与权限)
          </label>

          <div>
            <p class="mb-2 text-sm font-semibold text-slate-700">权限</p>
            <PermissionPicker v-model="form.permissions" :groups="groups" />
          </div>

          <div class="flex items-center gap-3 pt-2">
            <button
              class="rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-600 disabled:opacity-50"
              :disabled="saving"
              @click="save"
            >
              {{ saving ? '保存中...' : '保存' }}
            </button>
            <button
              class="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600"
              @click="showForm = false"
            >
              取消
            </button>
            <span v-if="message" class="text-sm text-red-500">{{ message }}</span>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>
