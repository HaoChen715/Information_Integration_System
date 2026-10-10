<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import AppLayout from '../components/AppLayout.vue'
import * as dataApi from '../api/data'
import type { BaserowField, Dataset } from '../api/data'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()

const READONLY_TYPES = new Set([
  'created_on',
  'last_modified',
  'auto_number',
  'formula',
  'lookup',
  'rollup',
  'created_by',
  'last_modified_by',
  'file',
  'link_row',
  'multiple_collaborators',
])

const datasets = ref<Dataset[]>([])
const activeKey = ref('')
const fields = ref<BaserowField[]>([])
const rows = ref<Record<string, unknown>[]>([])
const count = ref(0)
const page = ref(1)
const size = 50
const search = ref('')
const loading = ref(false)
const message = ref('')

const canCreate = computed(() => auth.hasPermission('data:create'))
const canEdit = computed(() => auth.hasPermission('data:edit'))
const canDelete = computed(() => auth.hasPermission('data:delete'))

const activeDataset = computed(() => datasets.value.find((d) => d.key === activeKey.value))

const groupField = computed(() => fields.value.find((f) => f.type === 'single_select'))

const chartData = computed(() => {
  const f = groupField.value
  if (!f) return []
  const map = new Map<string, number>()
  for (const row of rows.value) {
    const v = row[f.name]
    const label = v && typeof v === 'object' && 'value' in v ? String((v as { value: string }).value) : '（空）'
    map.set(label, (map.get(label) || 0) + 1)
  }
  const entries = [...map.entries()].sort((a, b) => b[1] - a[1])
  const max = Math.max(1, ...entries.map((e) => e[1]))
  return entries.map(([label, n]) => ({ label, n, pct: Math.round((n / max) * 100) }))
})

function isEditable(field: BaserowField): boolean {
  return !READONLY_TYPES.has(field.type) && field.type !== 'multiple_select'
}

function formatValue(field: BaserowField, value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  if (field.type === 'single_select') {
    return typeof value === 'object' && value && 'value' in value ? String((value as { value: string }).value) : String(value)
  }
  if (field.type === 'multiple_select' && Array.isArray(value)) {
    return value.map((v) => (v && typeof v === 'object' && 'value' in v ? (v as { value: string }).value : v)).join('、')
  }
  if (field.type === 'boolean') return value ? '是' : '否'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

async function loadFields() {
  const ds = activeDataset.value
  if (!ds) return
  fields.value = await dataApi.fetchFields(ds.table_id)
}

async function loadRows() {
  const ds = activeDataset.value
  if (!ds) return
  loading.value = true
  message.value = ''
  try {
    const res = await dataApi.fetchRows(ds.table_id, { page: page.value, size, search: search.value || undefined })
    rows.value = res.results
    count.value = res.count
  } catch (err: unknown) {
    message.value = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '加载失败'
    rows.value = []
  } finally {
    loading.value = false
  }
}

async function init() {
  datasets.value = await dataApi.fetchDatasets()
  if (datasets.value.length) {
    activeKey.value = datasets.value[0].key
  }
}

watch(activeKey, async () => {
  page.value = 1
  await loadFields()
  await loadRows()
})

function applySearch() {
  page.value = 1
  loadRows()
}

onMounted(async () => {
  if (!auth.user) await auth.loadUser()
  await init()
  if (activeKey.value) {
    await loadFields()
    await loadRows()
  }
})

// ---- 编辑/新增 ----
const showEditor = ref(false)
const editingRow = ref<Record<string, unknown> | null>(null)
const form = ref<Record<string, unknown>>({})
const saving = ref(false)
const editorMsg = ref('')

const editableFields = computed(() => fields.value.filter(isEditable))

function openCreate() {
  editingRow.value = null
  const init: Record<string, unknown> = {}
  for (const f of editableFields.value) init[f.name] = f.type === 'boolean' ? false : ''
  form.value = init
  editorMsg.value = ''
  showEditor.value = true
}

function openEdit(row: Record<string, unknown>) {
  editingRow.value = row
  const init: Record<string, unknown> = {}
  for (const f of editableFields.value) {
    const v = row[f.name]
    if (f.type === 'boolean') init[f.name] = Boolean(v)
    else if (f.type === 'single_select') init[f.name] = v && typeof v === 'object' ? (v as { id: number }).id : v ?? ''
    else if (f.type === 'number') init[f.name] = v ?? ''
    else init[f.name] = v ?? ''
  }
  form.value = init
  editorMsg.value = ''
  showEditor.value = true
}

async function save() {
  const ds = activeDataset.value
  if (!ds) return
  saving.value = true
  editorMsg.value = ''
  try {
    const payload: Record<string, unknown> = {}
    for (const f of editableFields.value) {
      let v = form.value[f.name]
      if (f.type === 'number' && v !== '' && v !== null) v = Number(v)
      if (v === '') v = null
      payload[f.name] = v
    }
    if (editingRow.value) {
      await dataApi.updateRow(ds.table_id, editingRow.value.id as number, payload)
    } else {
      await dataApi.createRow(ds.table_id, payload)
    }
    showEditor.value = false
    await loadRows()
  } catch (err: unknown) {
    editorMsg.value = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '保存失败'
  } finally {
    saving.value = false
  }
}

async function removeRow(row: Record<string, unknown>) {
  const ds = activeDataset.value
  if (!ds) return
  if (!confirm('确认删除该行数据?')) return
  try {
    await dataApi.deleteRow(ds.table_id, row.id as number)
    await loadRows()
  } catch (err: unknown) {
    alert((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '删除失败')
  }
}
</script>

<template>
  <AppLayout>
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold text-slate-800">数据看板</h1>
        <p class="mt-1 text-sm text-slate-500">
          Baserow 数据 · 共 {{ count }} 条
          <span v-if="!auth.isAdmin" class="text-slate-400">(仅显示本部门数据)</span>
        </p>
      </div>
      <div class="flex items-center gap-2">
        <select
          v-if="datasets.length > 1"
          v-model="activeKey"
          class="rounded-lg border border-slate-200 px-3 py-2 text-sm"
        >
          <option v-for="d in datasets" :key="d.key" :value="d.key">{{ d.name }}</option>
        </select>
        <input
          v-model="search"
          placeholder="搜索"
          class="rounded-lg border border-slate-200 px-3 py-2 text-sm"
          @keyup.enter="applySearch"
        />
        <button class="rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50" @click="applySearch">
          搜索
        </button>
        <button
          v-if="canCreate"
          class="rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-600"
          @click="openCreate"
        >
          新增
        </button>
      </div>
    </div>

    <p v-if="message" class="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-500">{{ message }}</p>

    <!-- 图表 -->
    <div v-if="chartData.length" class="mt-6 rounded-2xl border border-slate-200 bg-white p-5">
      <p class="text-sm font-semibold text-slate-700">分布(按「{{ groupField?.name }}」)</p>
      <div class="mt-4 space-y-3">
        <div v-for="item in chartData" :key="item.label" class="flex items-center gap-3">
          <span class="w-24 shrink-0 truncate text-xs text-slate-500">{{ item.label }}</span>
          <div class="h-4 flex-1 overflow-hidden rounded-full bg-slate-100">
            <div
              class="h-full rounded-full bg-gradient-to-r from-indigo-500 to-cyan-500"
              :style="{ width: item.pct + '%' }"
            />
          </div>
          <span class="w-8 shrink-0 text-right text-xs text-slate-500">{{ item.n }}</span>
        </div>
      </div>
    </div>

    <!-- 表格 -->
    <div class="mt-6 overflow-auto rounded-2xl border border-slate-200 bg-white">
      <table class="w-full text-sm">
        <thead class="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-400">
          <tr>
            <th v-for="f in fields" :key="f.id" class="whitespace-nowrap px-4 py-3">{{ f.name }}</th>
            <th v-if="canEdit || canDelete" class="px-4 py-3">操作</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          <tr v-for="row in rows" :key="String(row.id)" class="hover:bg-slate-50">
            <td v-for="f in fields" :key="f.id" class="whitespace-nowrap px-4 py-2.5 text-slate-600">
              {{ formatValue(f, row[f.name]) }}
            </td>
            <td v-if="canEdit || canDelete" class="whitespace-nowrap px-4 py-2.5">
              <button v-if="canEdit" class="mr-3 text-indigo-600 hover:underline" @click="openEdit(row)">编辑</button>
              <button v-if="canDelete" class="text-red-500 hover:underline" @click="removeRow(row)">删除</button>
            </td>
          </tr>
          <tr v-if="!loading && !rows.length">
            <td :colspan="fields.length + 1" class="px-4 py-10 text-center text-slate-400">暂无数据</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 编辑弹层 -->
    <div v-if="showEditor" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4" @click.self="showEditor = false">
      <div class="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-white p-6 shadow-xl">
        <div class="flex items-center justify-between">
          <h2 class="text-lg font-bold text-slate-800">{{ editingRow ? '编辑数据' : '新增数据' }}</h2>
          <button class="text-slate-400 hover:text-slate-600" @click="showEditor = false">✕</button>
        </div>
        <div class="mt-5 space-y-4">
          <label v-for="f in editableFields" :key="f.id" class="block">
            <span class="mb-1 block text-sm text-slate-600">{{ f.name }}</span>
            <select
              v-if="f.type === 'single_select'"
              v-model="form[f.name]"
              class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            >
              <option value="">（空）</option>
              <option v-for="o in f.select_options" :key="o.id" :value="o.id">{{ o.value }}</option>
            </select>
            <input
              v-else-if="f.type === 'boolean'"
              v-model="form[f.name]"
              type="checkbox"
              class="h-4 w-4 accent-indigo-500"
            />
            <input
              v-else-if="f.type === 'number'"
              v-model="form[f.name]"
              type="number"
              class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            />
            <input
              v-else-if="f.type === 'date'"
              v-model="form[f.name]"
              type="date"
              class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            />
            <input
              v-else
              v-model="form[f.name]"
              type="text"
              class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            />
          </label>
        </div>
        <div class="mt-6 flex items-center gap-3">
          <button
            class="rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-600 disabled:opacity-50"
            :disabled="saving"
            @click="save"
          >
            {{ saving ? '保存中...' : '保存' }}
          </button>
          <span v-if="editorMsg" class="text-sm text-red-500">{{ editorMsg }}</span>
        </div>
      </div>
    </div>
  </AppLayout>
</template>
