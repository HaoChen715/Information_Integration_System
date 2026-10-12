<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import AppLayout from '../components/AppLayout.vue'
import * as dataApi from '../api/data'
import type { BaserowField, Dataset, DataStatus } from '../api/data'
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
const status = ref<DataStatus | null>(null)
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

// 空间 -> 库 -> 表 树
const tree = computed(() => {
  const wsMap = new Map<string, Map<string, Dataset[]>>()
  for (const d of datasets.value) {
    if (!wsMap.has(d.workspace)) wsMap.set(d.workspace, new Map())
    const dbMap = wsMap.get(d.workspace)!
    const dbKey = d.database || '（默认库）'
    if (!dbMap.has(dbKey)) dbMap.set(dbKey, [])
    dbMap.get(dbKey)!.push(d)
  }
  return [...wsMap.entries()].map(([workspace, dbMap]) => ({
    workspace,
    databases: [...dbMap.entries()].map(([database, tables]) => ({ database, tables })),
  }))
})

const groupField = computed(() => fields.value.find((f) => f.type === 'single_select'))

const chartData = computed(() => {
  const f = groupField.value
  if (!f) return []
  const map = new Map<string, number>()
  for (const row of rows.value) {
    const v = row[f.name]
    const label =
      v && typeof v === 'object' && 'value' in v
        ? String((v as { value: string }).value)
        : '（空）'
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
    return typeof value === 'object' && value && 'value' in value
      ? String((value as { value: string }).value)
      : String(value)
  }
  if (field.type === 'multiple_select' && Array.isArray(value)) {
    return value
      .map((v) => (v && typeof v === 'object' && 'value' in v ? (v as { value: string }).value : v))
      .join('、')
  }
  if (field.type === 'boolean') return value ? '是' : '否'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

async function loadFields() {
  const ds = activeDataset.value
  if (!ds) {
    fields.value = []
    return
  }
  fields.value = await dataApi.fetchFields(ds.table_id)
}

async function loadRows() {
  const ds = activeDataset.value
  if (!ds) {
    rows.value = []
    count.value = 0
    return
  }
  loading.value = true
  message.value = ''
  try {
    const res = await dataApi.fetchRows(ds.table_id, {
      page: page.value,
      size,
      search: search.value || undefined,
    })
    rows.value = res.results
    count.value = res.count
  } catch (err: unknown) {
    message.value =
      (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '加载失败'
    rows.value = []
  } finally {
    loading.value = false
  }
}

async function init() {
  try {
    status.value = await dataApi.fetchStatus()
  } catch {
    status.value = null
  }
  try {
    datasets.value = await dataApi.fetchDatasets()
  } catch (err: unknown) {
    datasets.value = []
    message.value =
      (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '获取数据集失败'
  }
  if (datasets.value.length) activeKey.value = datasets.value[0].key
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
  const initForm: Record<string, unknown> = {}
  for (const f of editableFields.value) initForm[f.name] = f.type === 'boolean' ? false : ''
  form.value = initForm
  editorMsg.value = ''
  showEditor.value = true
}

function openEdit(row: Record<string, unknown>) {
  editingRow.value = row
  const initForm: Record<string, unknown> = {}
  for (const f of editableFields.value) {
    const v = row[f.name]
    if (f.type === 'boolean') initForm[f.name] = Boolean(v)
    else if (f.type === 'single_select')
      initForm[f.name] = v && typeof v === 'object' ? (v as { id: number }).id : v ?? ''
    else initForm[f.name] = v ?? ''
  }
  form.value = initForm
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
    editorMsg.value =
      (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '保存失败'
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
          <template v-if="activeDataset">
            {{ activeDataset.workspace }} / {{ activeDataset.database || '默认库' }} /
            {{ activeDataset.table }} · 共 {{ count }} 条
          </template>
          <template v-else>Baserow 数据</template>
          <span v-if="!auth.isAdmin" class="text-slate-400">(仅显示本部门数据)</span>
        </p>
      </div>
      <div class="flex items-center gap-2">
        <input
          v-model="search"
          placeholder="搜索"
          class="rounded-lg border border-slate-200 px-3 py-2 text-sm"
          @keyup.enter="applySearch"
        />
        <button
          class="rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50"
          @click="applySearch"
        >
          搜索
        </button>
        <button
          v-if="canCreate && activeDataset"
          class="rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-600"
          @click="openCreate"
        >
          新增
        </button>
      </div>
    </div>

    <div class="mt-6 grid gap-6 lg:grid-cols-4">
      <!-- 左侧:空间 -> 库 -> 表 -->
      <div class="rounded-2xl border border-slate-200 bg-white p-4 lg:col-span-1">
        <p class="mb-2 px-2 text-sm font-semibold text-slate-700">数据源</p>

        <div v-if="!datasets.length" class="rounded-lg bg-amber-50 px-3 py-3 text-xs text-amber-700">
          <p class="font-medium">暂无可用的数据源</p>
          <p class="mt-1">
            {{ status?.error || '请在部署 .env 配置 Baserow(推荐 BASEROW_USER_EMAIL/PASSWORD 自动发现)。' }}
          </p>
        </div>

        <div v-else class="space-y-3">
          <div v-for="ws in tree" :key="ws.workspace">
            <p class="px-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
              {{ ws.workspace }}
            </p>
            <div v-for="db in ws.databases" :key="db.database" class="mt-1">
              <p class="px-2 py-0.5 text-xs text-slate-500">{{ db.database }}</p>
              <ul>
                <li v-for="t in db.tables" :key="t.key">
                  <button
                    class="flex w-full items-center justify-between rounded-lg px-3 py-1.5 text-left text-sm transition"
                    :class="
                      activeKey === t.key
                        ? 'bg-indigo-50 text-indigo-700'
                        : 'text-slate-600 hover:bg-slate-50'
                    "
                    @click="activeKey = t.key"
                  >
                    <span class="truncate">{{ t.table }}</span>
                  </button>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧:图表 + 表格 -->
      <div class="space-y-6 lg:col-span-3">
        <p v-if="message" class="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-500">{{ message }}</p>

        <div v-if="!activeDataset" class="rounded-2xl border border-slate-200 bg-white px-6 py-16 text-center text-slate-400">
          请选择左侧的数据表
        </div>

        <template v-else>
          <div v-if="chartData.length" class="rounded-2xl border border-slate-200 bg-white p-5">
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

          <div class="overflow-auto rounded-2xl border border-slate-200 bg-white">
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
        </template>
      </div>
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
