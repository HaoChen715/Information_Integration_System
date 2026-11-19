<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppLayout from '../components/AppLayout.vue'
import * as dtApi from '../api/datatables'
import type { DataField, DataRecord, DataTable } from '../api/datatables'

const route = useRoute()
const router = useRouter()

const code = computed(() => String(route.params.code || ''))
const table = ref<DataTable | null>(null)
const rows = ref<DataRecord[]>([])
const loading = ref(false)
const error = ref('')
const search = ref('')
const groupBy = ref('')
const filters = ref<Record<string, string>>({})
const detail = ref<DataRecord | null>(null)

const GROUP_COLORS = ['#eef2ff', '#ecfdf5', '#fffbeb', '#fef2f2', '#ecfeff', '#faf5ff', '#f1f5f9', '#fdf2f8']
const OPTION_COLORS = ['#e0e7ff', '#dcfce7', '#fef3c7', '#fee2e2', '#cffafe', '#f3e8ff', '#f1f5f9', '#fce7f3']

const fields = computed<DataField[]>(() => table.value?.fields ?? [])
const titleField = computed<DataField | undefined>(() => {
  const key = table.value?.title_field
  return fields.value.find((f) => f.key === key) ?? fields.value[0]
})
const statusField = computed<DataField | undefined>(
  () => fields.value.find((f) => f.type === 'single_select'),
)
const filterableFields = computed<DataField[]>(() =>
  fields.value.filter((f) => f.type === 'single_select' || f.type === 'multiple_select' || f.type === 'boolean'),
)
const cardFields = computed<DataField[]>(() =>
  fields.value
    .filter((f) => f.key !== titleField.value?.key && f.key !== statusField.value?.key)
    .slice(0, 3),
)

const departmentOptions = computed(() => {
  const set = new Set<string>()
  for (const r of rows.value) if (r.department) set.add(r.department)
  return [...set].sort()
})

const activeFilters = computed(() =>
  Object.entries(filters.value)
    .filter(([, v]) => v !== '')
    .map(([key, value]) => ({
      key,
      label: key === '__department' ? '部门' : fields.value.find((f) => f.key === key)?.label || key,
      value,
    })),
)

function cellText(field: DataField | undefined, value: unknown): string {
  if (!field || value === null || value === undefined || value === '') return ''
  if (field.type === 'boolean') return value ? '是' : '否'
  if (field.type === 'multiple_select' && Array.isArray(value)) return value.join('、')
  return String(value)
}

function optionColor(field: DataField, value: string): string {
  const found = field.options.find((o) => o.value === value)
  return found?.color || OPTION_COLORS[Math.abs(hash(value)) % OPTION_COLORS.length]
}

function hash(text: string): number {
  let h = 0
  for (let i = 0; i < text.length; i++) h = (h * 31 + text.charCodeAt(i)) | 0
  return h
}

function selectValues(field: DataField, value: unknown): string[] {
  if (field.type === 'multiple_select') return Array.isArray(value) ? value.map(String) : []
  if (value === null || value === undefined || value === '') return []
  return [String(value)]
}

function recordTitle(record: DataRecord): string {
  const f = titleField.value
  if (!f) return `#${record.id}`
  return cellText(f, record.data[f.key]) || `#${record.id}`
}

function statusText(row: DataRecord): string {
  const f = statusField.value
  return f ? cellText(f, row.data[f.key]) : ''
}

function statusColor(row: DataRecord): string {
  const f = statusField.value
  const value = statusText(row)
  return f && value ? optionColor(f, value) : '#f1f5f9'
}

function valuesOf(field: DataField): string[] {
  const set = new Set<string>()
  for (const r of rows.value) {
    const values = field.type === 'multiple_select' ? selectValues(field, r.data[field.key]) : [cellText(field, r.data[field.key])]
    for (const v of values) if (v) set.add(v)
  }
  return [...set].sort()
}

const filteredRows = computed(() => {
  const q = search.value.trim().toLowerCase()
  return rows.value.filter((row) => {
    if (q) {
      const text = Object.values(row.data).map(String).join(' ').toLowerCase()
      if (!text.includes(q) && !row.owner_username.toLowerCase().includes(q)) return false
    }
    for (const [key, value] of Object.entries(filters.value)) {
      if (!value) continue
      if (key === '__department') {
        if ((row.department || '') !== value) return false
        continue
      }
      const field = fields.value.find((f) => f.key === key)
      if (!field) continue
      if (field.type === 'multiple_select') {
        if (!selectValues(field, row.data[key]).includes(value)) return false
      } else if (cellText(field, row.data[key]) !== value) {
        return false
      }
    }
    return true
  })
})

const groups = computed(() => {
  const field = fields.value.find((f) => f.key === groupBy.value)
  if (!field) return [{ key: '_', label: '全部数据', rows: filteredRows.value }]
  const map = new Map<string, DataRecord[]>()
  for (const row of filteredRows.value) {
    const label = cellText(field, row.data[field.key]) || '（空）'
    if (!map.has(label)) map.set(label, [])
    map.get(label)!.push(row)
  }
  return [...map.entries()]
    .sort((a, b) => b[1].length - a[1].length)
    .map(([label, items]) => ({ key: label, label, rows: items }))
})

const summary = computed(() => ({
  total: filteredRows.value.length,
  all: rows.value.length,
  groups: groupBy.value ? groups.value.length : 0,
  filters: activeFilters.value.length,
}))

async function loadTable() {
  loading.value = true
  error.value = ''
  try {
    const list = await dtApi.listTables()
    const found = list.find((t) => t.code === code.value)
    if (!found) {
      error.value = '数据表不存在或无权访问'
      table.value = null
      rows.value = []
      return
    }
    table.value = found
    if (!groupBy.value || !found.fields.some((f) => f.key === groupBy.value)) {
      const firstGroupable = found.fields.find((f) => f.type === 'single_select')
      groupBy.value = firstGroupable?.key || ''
    }
  } catch (err: unknown) {
    error.value =
      (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '加载数据表失败'
  } finally {
    loading.value = false
  }
}

async function loadRows() {
  if (!code.value) return
  loading.value = true
  error.value = ''
  try {
    rows.value = await dtApi.listRecords(code.value, search.value.trim() || undefined)
  } catch (err: unknown) {
    error.value =
      (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '加载记录失败'
    rows.value = []
  } finally {
    loading.value = false
  }
}

async function load() {
  filters.value = {}
  await loadTable()
  await loadRows()
}

function removeFilter(key: string) {
  const next = { ...filters.value }
  delete next[key]
  filters.value = next
}

function clearFilters() {
  filters.value = {}
  search.value = ''
  void loadRows()
}

function backToTable() {
  router.push({ path: '/department/data', query: { table: code.value } })
}

function openDetail(row: DataRecord) {
  detail.value = row
}

watch(code, () => {
  void load()
})

onMounted(load)
</script>

<template>
  <AppLayout wide>
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div class="min-w-0">
        <button class="text-sm text-slate-500 hover:text-indigo-600" @click="backToTable">← 返回数据看板</button>
        <h1 class="mt-1 truncate text-2xl font-bold text-slate-800">
          {{ table?.name || '数据表面板' }}
          <span v-if="table" class="ml-2 font-mono text-xs font-normal text-slate-400">{{ table.code }}</span>
        </h1>
        <p class="mt-1 text-sm text-slate-500">
          {{ table?.description || '按字段分组的小面板视图' }}
          <span v-if="table?.scope_by_department" class="ml-2 text-slate-400">
            · {{ table.visible_departments?.join('、') || '未设置部门' }}
          </span>
        </p>
      </div>
      <button
        class="rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50"
        @click="backToTable"
      >
        表格视图
      </button>
    </div>

    <p v-if="error" class="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-500">{{ error }}</p>

    <div class="mt-4 grid gap-3 sm:grid-cols-3">
      <div class="rounded-xl border border-slate-200 bg-white px-4 py-3">
        <p class="text-xs text-slate-400">当前记录</p>
        <p class="mt-0.5 text-2xl font-bold text-slate-800">{{ summary.total }}</p>
      </div>
      <div class="rounded-xl border border-slate-200 bg-white px-4 py-3">
        <p class="text-xs text-slate-400">{{ groupBy ? '分组数' : '全部记录' }}</p>
        <p class="mt-0.5 text-2xl font-bold text-indigo-600">{{ groupBy ? summary.groups : summary.all }}</p>
      </div>
      <div class="rounded-xl border border-slate-200 bg-white px-4 py-3">
        <p class="text-xs text-slate-400">生效筛选</p>
        <p class="mt-0.5 text-2xl font-bold text-emerald-600">{{ summary.filters }}</p>
      </div>
    </div>

    <div class="mt-4 rounded-2xl border border-slate-200 bg-white p-4">
      <div class="flex flex-wrap items-end gap-3">
        <label class="block">
          <span class="mb-1 block text-xs text-slate-500">搜索</span>
          <input
            v-model="search"
            placeholder="标题/内容/创建者"
            class="w-52 rounded-lg border border-slate-200 px-3 py-1.5 text-sm"
            @keyup.enter="loadRows"
          />
        </label>
        <label class="block">
          <span class="mb-1 block text-xs text-slate-500">分组字段</span>
          <select v-model="groupBy" class="w-40 rounded-lg border border-slate-200 px-3 py-1.5 text-sm">
            <option value="">不分组</option>
            <option v-for="f in fields" :key="f.id" :value="f.key">{{ f.label }}</option>
          </select>
        </label>
        <label v-for="f in filterableFields.slice(0, 3)" :key="f.id" class="block">
          <span class="mb-1 block text-xs text-slate-500">{{ f.label }}</span>
          <select v-model="filters[f.key]" class="w-36 rounded-lg border border-slate-200 px-3 py-1.5 text-sm">
            <option value="">全部</option>
            <option v-for="v in valuesOf(f)" :key="v" :value="v">{{ v }}</option>
          </select>
        </label>
        <label v-if="departmentOptions.length" class="block">
          <span class="mb-1 block text-xs text-slate-500">部门</span>
          <select v-model="filters.__department" class="w-36 rounded-lg border border-slate-200 px-3 py-1.5 text-sm">
            <option value="">全部</option>
            <option v-for="d in departmentOptions" :key="d" :value="d">{{ d }}</option>
          </select>
        </label>
        <button class="rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50" @click="loadRows">
          搜索
        </button>
        <button class="rounded-lg px-3 py-1.5 text-sm text-slate-500 hover:text-indigo-600" @click="clearFilters">
          重置
        </button>
      </div>

      <div v-if="activeFilters.length" class="mt-3 flex flex-wrap items-center gap-2">
        <span class="text-xs text-slate-400">筛选:</span>
        <button
          v-for="f in activeFilters"
          :key="f.key"
          class="group inline-flex items-center gap-1 rounded-full bg-indigo-50 px-2.5 py-1 text-xs text-indigo-700 hover:bg-indigo-100"
          @click="removeFilter(f.key)"
        >
          {{ f.label }} = {{ f.value }}
          <span class="text-indigo-400 group-hover:text-indigo-700">✕</span>
        </button>
      </div>
    </div>

    <div v-if="loading" class="mt-10 text-center text-sm text-slate-400">加载中...</div>
    <div v-else-if="!filteredRows.length" class="mt-6 rounded-2xl border border-dashed border-slate-200 bg-white px-6 py-16 text-center text-slate-400">
      暂无匹配数据
    </div>

    <div v-else class="mt-6 space-y-8">
      <section v-for="(g, gi) in groups" :key="g.key">
        <div class="flex items-center gap-2">
          <span
            class="rounded-lg px-2.5 py-1 text-xs font-medium text-slate-700"
            :style="groupBy ? { background: GROUP_COLORS[gi % GROUP_COLORS.length] } : {}"
          >
            {{ g.label }}
          </span>
          <span class="text-xs text-slate-400">{{ g.rows.length }} 条</span>
        </div>

        <div class="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
          <button
            v-for="row in g.rows"
            :key="row.id"
            class="group flex flex-col rounded-xl border border-slate-200 bg-white p-4 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-indigo-300 hover:shadow-lg"
            @click="openDetail(row)"
          >
            <div class="flex items-start justify-between gap-2">
              <p class="truncate text-sm font-semibold text-slate-800">{{ recordTitle(row) }}</p>
              <span
                v-if="statusText(row)"
                class="shrink-0 rounded-full px-2 py-0.5 text-[11px] text-slate-700"
                :style="{ background: statusColor(row) }"
              >
                {{ statusText(row) }}
              </span>
            </div>

            <div class="mt-3 space-y-1.5">
              <div v-for="f in cardFields" :key="f.id" class="flex items-baseline justify-between gap-2 text-xs">
                <span class="shrink-0 text-slate-400">{{ f.label }}</span>
                <span class="truncate text-right text-slate-600">
                  {{ cellText(f, row.data[f.key]) || '—' }}
                </span>
              </div>
            </div>

            <div class="mt-3 flex items-center justify-between border-t border-slate-100 pt-2 text-[11px] text-slate-400">
              <span class="truncate">{{ row.department || '—' }}</span>
              <span class="shrink-0">{{ new Date(row.updated_at).toLocaleDateString() }}</span>
            </div>
          </button>
        </div>
      </section>
    </div>

    <div
      v-if="detail"
      class="fixed inset-0 z-50 flex justify-end bg-slate-900/40 backdrop-blur-sm"
      @click.self="detail = null"
    >
      <div class="h-full w-full max-w-md overflow-y-auto bg-white p-6 shadow-2xl">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <h2 class="truncate text-lg font-bold text-slate-800">{{ recordTitle(detail) }}</h2>
            <p class="mt-0.5 text-xs text-slate-400">{{ detail.department || '未设置部门' }} · {{ detail.owner_username }}</p>
          </div>
          <button class="text-slate-400 hover:text-slate-600" @click="detail = null">✕</button>
        </div>

        <div class="mt-5 space-y-2">
          <div v-for="f in fields" :key="f.id" class="rounded-lg border border-slate-100 bg-slate-50/50 px-3 py-2">
            <p class="text-[11px] text-slate-400">{{ f.label }}</p>
            <div class="mt-0.5 text-sm text-slate-700">
              <span
                v-if="f.type === 'single_select' || f.type === 'multiple_select'"
                class="inline-flex flex-wrap gap-1"
              >
                <span
                  v-for="v in selectValues(f, detail.data[f.key])"
                  :key="v"
                  class="rounded-full px-2 py-0.5 text-xs text-slate-700"
                  :style="{ background: optionColor(f, v) }"
                >
                  {{ v }}
                </span>
                <span v-if="!selectValues(f, detail.data[f.key]).length" class="text-slate-300">—</span>
              </span>
              <span v-else-if="f.type === 'boolean'">{{ detail.data[f.key] ? '是' : '否' }}</span>
              <span v-else class="whitespace-pre-wrap">{{ cellText(f, detail.data[f.key]) || '—' }}</span>
            </div>
          </div>
        </div>

        <p class="mt-4 text-[11px] text-slate-400">
          创建 {{ new Date(detail.created_at).toLocaleString() }} · 更新 {{ new Date(detail.updated_at).toLocaleString() }}
        </p>

        <div class="mt-5 flex gap-2">
          <button class="rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-600" @click="backToTable">
            去表格视图编辑
          </button>
          <button class="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600" @click="detail = null">关闭</button>
        </div>
      </div>
    </div>
  </AppLayout>
</template>
