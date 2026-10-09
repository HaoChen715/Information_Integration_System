<script setup lang="ts">
import { onMounted, ref } from 'vue'

import AppLayout from '../../components/AppLayout.vue'
import * as adminApi from '../../api/admin'
import type { Department } from '../../api/admin'

const departments = ref<Department[]>([])
const name = ref('')
const description = ref('')
const editingId = ref<number | null>(null)
const message = ref('')

async function load() {
  departments.value = await adminApi.fetchDepartments()
}

function reset() {
  editingId.value = null
  name.value = ''
  description.value = ''
}

function startEdit(d: Department) {
  editingId.value = d.id
  name.value = d.name
  description.value = d.description ?? ''
}

async function save() {
  message.value = ''
  if (!name.value.trim()) return
  try {
    if (editingId.value === null) {
      await adminApi.createDepartment({ name: name.value.trim(), description: description.value })
    } else {
      await adminApi.updateDepartment(editingId.value, {
        name: name.value.trim(),
        description: description.value,
      })
    }
    reset()
    await load()
  } catch (err: unknown) {
    message.value =
      (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '保存失败'
  }
}

async function remove(d: Department) {
  if (!confirm(`确认删除部门「${d.name}」?`)) return
  try {
    await adminApi.deleteDepartment(d.id)
    await load()
  } catch (err: unknown) {
    alert((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '删除失败')
  }
}

onMounted(load)
</script>

<template>
  <AppLayout>
    <h1 class="text-2xl font-bold text-slate-800">部门管理</h1>
    <p class="mt-1 text-sm text-slate-500">维护部门列表,用户编辑时的部门下拉框来源于此。</p>

    <div class="mt-6 rounded-2xl border border-slate-200 bg-white p-5">
      <p class="mb-3 text-sm font-semibold text-slate-700">
        {{ editingId === null ? '新增部门' : '编辑部门' }}
      </p>
      <div class="flex flex-col gap-3 sm:flex-row">
        <input
          v-model="name"
          placeholder="部门名称"
          class="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-indigo-400"
        />
        <input
          v-model="description"
          placeholder="说明(可选)"
          class="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-indigo-400"
        />
        <button
          class="rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-600"
          @click="save"
        >
          {{ editingId === null ? '添加' : '保存' }}
        </button>
        <button
          v-if="editingId !== null"
          class="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600"
          @click="reset"
        >
          取消
        </button>
      </div>
      <p v-if="message" class="mt-2 text-sm text-red-500">{{ message }}</p>
    </div>

    <div class="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white">
      <table class="w-full text-sm">
        <thead class="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-400">
          <tr>
            <th class="px-5 py-3">部门名称</th>
            <th class="px-5 py-3">说明</th>
            <th class="px-5 py-3">操作</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          <tr v-for="d in departments" :key="d.id">
            <td class="px-5 py-3 font-medium text-slate-700">{{ d.name }}</td>
            <td class="px-5 py-3 text-slate-500">{{ d.description || '—' }}</td>
            <td class="px-5 py-3">
              <button class="mr-3 text-indigo-600 hover:underline" @click="startEdit(d)">编辑</button>
              <button class="text-red-500 hover:underline" @click="remove(d)">删除</button>
            </td>
          </tr>
          <tr v-if="!departments.length">
            <td colspan="3" class="px-5 py-8 text-center text-slate-400">暂无部门</td>
          </tr>
        </tbody>
      </table>
    </div>
  </AppLayout>
</template>
