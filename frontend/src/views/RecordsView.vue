<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import AppLayout from '../components/AppLayout.vue'
import client from '../api/client'
import { useAuthStore } from '../stores/auth'

interface RecordItem {
  id: number
  title: string
  content: string | null
  owner_username: string
  department: string | null
  created_at: string
}

const auth = useAuthStore()
const records = ref<RecordItem[]>([])
const title = ref('')
const content = ref('')
const error = ref('')

const canCreate = computed(() => auth.hasPermission('record:create'))
const scopeLabel = computed(() => {
  const scope = auth.scopeOf('record:view')
  return scope === 'all' ? '全部数据' : scope === 'dept' ? '本部门数据' : '仅本人数据'
})

async function load() {
  const { data } = await client.get<RecordItem[]>('/records')
  records.value = data
}

async function create() {
  error.value = ''
  if (!title.value.trim()) return
  try {
    await client.post('/records', { title: title.value.trim(), content: content.value })
    title.value = ''
    content.value = ''
    await load()
  } catch (err: unknown) {
    error.value =
      (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '创建失败'
  }
}

onMounted(load)
</script>

<template>
  <AppLayout>
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-slate-800">资料</h1>
        <p class="mt-1 text-sm text-slate-500">
          当前可见范围:<span class="font-medium text-indigo-600">{{ scopeLabel }}</span>
        </p>
      </div>
    </div>

    <div v-if="canCreate" class="mt-6 rounded-2xl border border-slate-200 bg-white p-5">
      <p class="mb-3 text-sm font-semibold text-slate-700">新增资料</p>
      <div class="flex flex-col gap-3 sm:flex-row">
        <input
          v-model="title"
          placeholder="标题"
          class="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-indigo-400"
        />
        <input
          v-model="content"
          placeholder="内容(可选)"
          class="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-indigo-400"
        />
        <button
          class="rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-600"
          @click="create"
        >
          添加
        </button>
      </div>
      <p v-if="error" class="mt-2 text-sm text-red-500">{{ error }}</p>
    </div>

    <div class="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white">
      <table class="w-full text-sm">
        <thead class="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-400">
          <tr>
            <th class="px-5 py-3">标题</th>
            <th class="px-5 py-3">归属人</th>
            <th class="px-5 py-3">部门</th>
            <th class="px-5 py-3">创建时间</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          <tr v-for="r in records" :key="r.id">
            <td class="px-5 py-3 font-medium text-slate-700">{{ r.title }}</td>
            <td class="px-5 py-3 text-slate-500">{{ r.owner_username }}</td>
            <td class="px-5 py-3 text-slate-500">{{ r.department || '—' }}</td>
            <td class="px-5 py-3 text-slate-400">{{ new Date(r.created_at).toLocaleString() }}</td>
          </tr>
          <tr v-if="!records.length">
            <td colspan="4" class="px-5 py-8 text-center text-slate-400">暂无数据</td>
          </tr>
        </tbody>
      </table>
    </div>
  </AppLayout>
</template>
