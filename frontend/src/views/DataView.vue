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

const SELECT_COLORS: Record<string, string> = {
  blue: '#3b82f6',
  green: '#22c55e',
  red: '#ef4444',
  orange: '#f97316',
  yellow: '#eab308',
  purple: '#a855f7',
  pink: '#ec4899',
  cyan: '#06b6d4',
  gray: '#64748b',
  brown: '#92400e',
  'dark-green': '#15803d',
  'dark-blue': '#1d4ed8',
  'dark-red': '#b91c1c',
  'dark-orange': '#c2410c',
  'dark-yellow': '#a16207',
  'dark-purple': '#7e22ce',
  'dark-pink': '#be185d',
  'dark-cyan': '#0e7490',
}

const PAGE_SIZE = 200

const datasets = ref<Dataset[]>([])
const status = ref<DataStatus | null>(null)
const activeKey = ref('')
const fields = ref<BaserowField[]>([])
const rows = ref<Record<string, unknown>[]>([])
const count = ref(0)
const search = ref('')
const loading = ref(false)
const message = ref('')

const canCreate = computed(() => auth.hasPermission('data:create'))
const canEdit = computed(() => auth.hasPermission('data:edit'))
const canDelete = computed(() => auth.hasPermission('data:delete'))
const activeDataset = computed(() => datasets.value.find((d) => d.key === activeKey.value))

const stage = ref<'filter' | 'jump' | 'display'>('filter')
const selectedFields = ref<string[]>([])
const filters = ref<Record<string, string>>({})
const confirmed = ref<Record<string, string>>({})

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

function cellLabel(field: BaserowField | undefined, value: unknown): string {
  if (value === null || value === undefined || value === '') return ''
  const type = field?.type
  if (type === 'single_select')
    return typeof value === 'object' && value && 'value' in value
      ? String((value as { value: string }).value)
      : String(value)
  if (type === 'multiple_select' && Array.isArray(value))
    return value
      .map((v) => (v && typeof v === 'object' && 'value' in v ? (v as { value: string }).value : v))
      .join('、')
  if (type === 'boolean') return value ? '是' : '否'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

function pills(field: BaserowField, value: unknown): { value: string; color: string }[] {
  const list = field.type === 'multiple_select' ? (Array.isArray(value) ? value : []) : [value]
  const out: { value: string; color: string }[] = []
  for (const v of list) {
    if (v && typeof v === 'object' && 'value' in v) {
      const obj = v as { value: string; color?: string }
      out.push({ value: obj.value, color: SELECT_COLORS[obj.color || 'gray'] || '#64748b' })
    }
  }
  return out
}

function fieldByName(name: string) {
  return fields.value.find((f) => f.name === name)
}

function valueOptions(name: string): string[] {
  const f = fieldByName(name)
  const set = new Set<string>()
  for (const row of rows.value) {
    const label = cellLabel(f, row[name])
    if (label) set.add(label)
  }
  return [...set].sort().slice(0, 100)
}

function toggleField(name: string) {
  const idx = selectedFields.value.indexOf(name)
  if (idx >= 0) {
    selectedFields.value.splice(idx, 1)
    delete filters.value[name]
  } else {
    selectedFields.value.push(name)
  }
}

const totalLoaded = computed(() => rows.value.length)

function filterCount(field: string, value: string): number {
  const f = fieldByName(field)
  if (value) return rows.value.filter((r) => cellLabel(f, r[field]) === value).length
  return rows.value.filter((r) => !cellLabel(f, r[field])).length
}

const jumpRows = computed(() =>
  Object.entries(confirmed.value).map(([field, value]) => {
    const c = filterCount(field, value)
    return { field, value, count: c, pct: totalLoaded.value ? Math.round((c / totalLoaded.value) * 100) : 0 }
  }),
)

function matches(row: Record<string, unknown>, skipField?: string): boolean {
  return Object.entries(confirmed.value).every(([field, value]) => {
    if (field === skipField) return true
    if (!value) return !cellLabel(fieldByName(field), row[field])
    return cellLabel(fieldByName(field), row[field]) === value
  })
}

const filteredRows = computed(() => rows.value.filter((row) => matches(row)))

// ---- 分析(排除自身分组字段,便于下钻切换) ----
const groupBy = ref('')
const chartType = ref<'bar' | 'pie'>('bar')

const chartRows = computed(() => rows.value.filter((row) => matches(row, groupBy.value)))

const analysis = computed(() => {
  const gf = fieldByName(groupBy.value)
  if (!gf) return []
  const map = new Map<string, number>()
  for (const row of chartRows.value) {
    const label = cellLabel(gf, row[gf.name])
    map.set(label, (map.get(label) || 0) + 1)
  }
  const entries = [...map.entries()].sort((a, b) => b[1] - a[1])
  const base = chartRows.value.length || 1
  const selected = confirmed.value[groupBy.value] ?? null
  return entries.slice(0, 12).map(([label, value], i) => ({
    label,
    display: label || '（空）',
    value,
    rowPct: Math.round((value / base) * 100),
    color: `hsl(${(i * 47) % 360} 70% 55%)`,
    selected: label === selected,
  }))
})

// 环形图切片
const RO = 80
const RI = 50
function arcPath(a0: number, a1: number): string {
  const p = (r: number, a: number) => [100 + r * Math.cos(a), 100 + r * Math.sin(a)]
  const [x0, y0] = p(RO, a0)
  const [x1, y1] = p(RO, a1)
  const [x2, y2] = p(RI, a1)
  const [x3, y3] = p(RI, a0)
  const large = a1 - a0 > Math.PI ? 1 : 0
  return `M${x0},${y0} A${RO},${RO} 0 ${large} 1 ${x1},${y1} L${x2},${y2} A${RI},${RI} 0 ${large} 0 ${x3},${y3} Z`
}
const pieSlices = computed(() => {
  const total = analysis.value.reduce((a, b) => a + b.value, 0) || 1
  let angle = -Math.PI / 2
  const slices: { d: string; color: string; label: string; display: string; value: number; rowPct: number; selected: boolean }[] = []
  const src = analysis.value.length === 1 ? [...analysis.value, { ...analysis.value[0] }] : analysis.value
  for (const s of src) {
    const frac = s.value / total
    const a0 = angle
    const a1 = angle + frac * 2 * Math.PI
    angle = a1
    slices.push({
      d: arcPath(a0, Math.min(a1, a0 + Math.PI * 2 - 0.0001)),
      color: s.color,
      label: s.label,
      display: s.display,
      value: s.value,
      rowPct: s.rowPct,
      selected: s.selected,
    })
  }
  return slices
})

function drill(field: string, label: string) {
  confirmed.value = { ...confirmed.value, [field]: label }
}

// ---- 加载 ----
async function loadFields() {
  const ds = activeDataset.value
  if (!ds) {
    fields.value = []
    return
  }
  fields.value = await dataApi.fetchFields(ds.table_id)
  groupBy.value =
    fields.value.find((f) => f.type === 'single_select')?.name || fields.value[0]?.name || ''
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
    const res = await dataApi.fetchRows(ds.table_id, { size: PAGE_SIZE, search: search.value || undefined })
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

function resetStages() {
  stage.value = 'filter'
  selectedFields.value = []
  filters.value = {}
  confirmed.value = {}
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
  resetStages()
  await loadFields()
  await loadRows()
})

function applySearch() {
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

function confirmFilters() {
  const clean: Record<string, string> = {}
  for (const [k, v] of Object.entries(filters.value)) if (selectedFields.value.includes(k) && v !== '') clean[k] = v
  confirmed.value = clean
  stage.value = 'jump'
}

function removeFilter(field: string) {
  const next = { ...confirmed.value }
  delete next[field]
  confirmed.value = next
}

// ---- 编辑能力标记 ----
function isEditable(field: BaserowField): boolean {
  return !READONLY_TYPES.has(field.type)
}

function normalizeValue(field: BaserowField, v: unknown): unknown {
  if (field.type === 'multiple_select') return Array.isArray(v) ? v : []
  if (field.type === 'number' && v !== '' && v !== null) return Number(v)
  if (v === '') return null
  return v
}

// ---- 维度分组(卡片面板) ----
const dimension = ref('')
const titleField = computed(() => fields.value[0])
const previewFields = computed(() => fields.value.filter((f) => f !== titleField.value).slice(0, 3))
const groups = computed(() => {
  const df = fieldByName(dimension.value)
  if (!df) return [{ key: '_', label: '全部', rows: filteredRows.value }]
  const map = new Map<string, Record<string, unknown>[]>()
  for (const row of filteredRows.value) {
    const label = cellLabel(df, row[df.name]) || '（空）'
    if (!map.has(label)) map.set(label, [])
    map.get(label)!.push(row)
  }
  return [...map.entries()]
    .sort((a, b) => b[1].length - a[1].length)
    .map(([label, rows]) => ({ key: label, label, rows }))
})

function enterDisplay() {
  const firstFilter = Object.keys(confirmed.value)[0]
  dimension.value = firstFilter || fields.value[0]?.name || ''
  stage.value = 'display'
}

// ---- 详情大面板 ----
const detailRow = ref<Record<string, unknown> | null>(null)
const detailEdit = ref(false)
const detailForm = ref<Record<string, unknown>>({})
const detailSaving = ref(false)
const detailMsg = ref('')

function openDetail(row: Record<string, unknown>) {
  detailRow.value = row
  detailEdit.value = false
  detailMsg.value = ''
}
function closeDetail() {
  detailRow.value = null
  detailEdit.value = false
}
function startDetailEdit() {
  if (!detailRow.value) return
  const initForm: Record<string, unknown> = {}
  for (const f of editableFields.value) {
    const v = detailRow.value[f.name]
    if (f.type === 'boolean') initForm[f.name] = Boolean(v)
    else if (f.type === 'single_select')
      initForm[f.name] = v && typeof v === 'object' ? (v as { id: number }).id : ''
    else if (f.type === 'multiple_select')
      initForm[f.name] = Array.isArray(v) ? v.map((x) => (x as { id: number }).id) : []
    else initForm[f.name] = v ?? ''
  }
  detailForm.value = initForm
  detailMsg.value = ''
  detailEdit.value = true
}
async function saveDetail() {
  const ds = activeDataset.value
  const row = detailRow.value
  if (!ds || !row) return
  detailSaving.value = true
  detailMsg.value = ''
  try {
    const payload: Record<string, unknown> = {}
    for (const f of editableFields.value) {
      payload[f.name] = normalizeValue(f, detailForm.value[f.name])
    }
    const updated = await dataApi.updateRow(ds.table_id, row.id as number, payload)
    Object.assign(row, updated)
    detailEdit.value = false
  } catch (err: unknown) {
    detailMsg.value =
      (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '保存失败'
  } finally {
    detailSaving.value = false
  }
}

async function removeRow(row: Record<string, unknown>) {
  const ds = activeDataset.value
  if (!ds) return
  if (!confirm('确认删除该行数据?')) return
  try {
    await dataApi.deleteRow(ds.table_id, row.id as number)
    closeDetail()
    await loadRows()
  } catch (err: unknown) {
    alert((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '删除失败')
  }
}

// ---- 新增弹层 ----
const showEditor = ref(false)
const form = ref<Record<string, unknown>>({})
const saving = ref(false)
const editorMsg = ref('')
const editableFields = computed(() => fields.value.filter(isEditable))

function openCreate() {
  const initForm: Record<string, unknown> = {}
  for (const f of editableFields.value)
    initForm[f.name] = f.type === 'boolean' ? false : f.type === 'multiple_select' ? [] : ''
  const deptField = fields.value.find((f) => f.type === 'single_select' && f.name.includes('部门'))
  if (deptField && auth.user?.department) {
    const opt = deptField.select_options?.find((o) => o.value === auth.user?.department)
    if (opt) initForm[deptField.name] = opt.id
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
      payload[f.name] = normalizeValue(f, form.value[f.name])
    }
    await dataApi.createRow(ds.table_id, payload)
    showEditor.value = false
    await loadRows()
  } catch (err: unknown) {
    editorMsg.value =
      (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '保存失败'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <AppLayout :wide="stage === 'display'">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold text-slate-800">数据看板</h1>
        <p class="mt-1 text-sm text-slate-500">
          <template v-if="activeDataset">
            {{ activeDataset.workspace }} / {{ activeDataset.database || '默认库' }} / {{ activeDataset.table }}
            · 共 {{ count }} 条
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
        <button class="rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50" @click="applySearch">
          搜索
        </button>
        <button
          v-if="canCreate && activeDataset && stage === 'display'"
          class="rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-600"
          @click="openCreate"
        >
          新增
        </button>
      </div>
    </div>

    <p v-if="message" class="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-500">{{ message }}</p>

    <!-- 展示阶段:全宽 -->
    <template v-if="activeDataset && stage === 'display'">
      <div class="mt-6 flex flex-wrap items-center justify-between gap-3">
        <div class="flex flex-wrap items-center gap-2">
          <span class="text-sm text-slate-500">当前筛选:</span>
          <button
            v-for="(v, k) in confirmed"
            :key="k"
            class="group inline-flex items-center gap-1 rounded-full bg-indigo-50 px-3 py-1 text-xs text-indigo-700 hover:bg-indigo-100"
            @click="removeFilter(k)"
          >
            {{ k }} = {{ v || '（空）' }}
            <span class="text-indigo-400 group-hover:text-indigo-700">✕</span>
          </button>
          <span v-if="!Object.keys(confirmed).length" class="text-sm text-slate-400">无(全部数据)</span>
        </div>
        <button class="rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-600" @click="stage = 'filter'">
          返回筛选
        </button>
      </div>

      <div class="mt-4 grid gap-4 sm:grid-cols-3">
        <div class="rounded-2xl border border-slate-200 bg-white p-5">
          <p class="text-xs uppercase tracking-wide text-slate-400">命中记录</p>
          <p class="mt-1 text-3xl font-bold text-slate-800">{{ filteredRows.length }}</p>
        </div>
        <div class="rounded-2xl border border-slate-200 bg-white p-5">
          <p class="text-xs uppercase tracking-wide text-slate-400">占全部</p>
          <p class="mt-1 text-3xl font-bold text-indigo-600">
            {{ totalLoaded ? Math.round((filteredRows.length / totalLoaded) * 100) : 0 }}%
          </p>
        </div>
        <div class="rounded-2xl border border-slate-200 bg-white p-5">
          <p class="text-xs uppercase tracking-wide text-slate-400">条件数</p>
          <p class="mt-1 text-3xl font-bold text-emerald-600">{{ Object.keys(confirmed).length }}</p>
        </div>
      </div>

      <div class="mt-6 grid gap-6 lg:grid-cols-4">
        <!-- 左:分布分析 -->
        <div class="rounded-2xl border border-slate-200 bg-white p-5 lg:col-span-1">
          <div class="flex items-center justify-between">
            <p class="text-sm font-semibold text-slate-700">分布分析</p>
            <div class="flex overflow-hidden rounded-lg border border-slate-200 text-xs">
              <button
                class="px-2.5 py-1 transition"
                :class="chartType === 'bar' ? 'bg-indigo-500 text-white' : 'text-slate-500 hover:bg-slate-50'"
                @click="chartType = 'bar'"
              >
                柱状
              </button>
              <button
                class="px-2.5 py-1 transition"
                :class="chartType === 'pie' ? 'bg-indigo-500 text-white' : 'text-slate-500 hover:bg-slate-50'"
                @click="chartType = 'pie'"
              >
                饼状
              </button>
            </div>
          </div>
          <label class="mt-3 flex items-center gap-2 text-sm text-slate-600">
            分组
            <select v-model="groupBy" class="flex-1 rounded-lg border border-slate-200 px-2 py-1.5 text-sm">
              <option v-for="f in fields" :key="f.id" :value="f.name">{{ f.name }}</option>
            </select>
          </label>

          <!-- 柱状 -->
          <div v-if="chartType === 'bar'" class="mt-4 space-y-2.5">
            <button
              v-for="item in analysis"
              :key="item.label"
              class="flex w-full items-center gap-3 rounded-lg px-2 py-1.5 text-left transition"
              :class="item.selected ? 'bg-indigo-50 ring-1 ring-indigo-200' : 'hover:bg-slate-50'"
              @click="drill(groupBy, item.label)"
            >
              <span class="w-20 shrink-0 truncate text-xs text-slate-500" :title="item.display">{{ item.display }}</span>
              <div class="h-5 flex-1 overflow-hidden rounded-full bg-slate-100">
                <div
                  class="flex h-full items-center justify-end rounded-full pr-1.5 text-[10px] font-medium text-white transition-all"
                  :style="{ width: Math.max(item.rowPct, 6) + '%', background: item.color }"
                >
                  {{ item.value }}
                </div>
              </div>
              <span class="w-10 shrink-0 text-right text-xs text-slate-400">{{ item.rowPct }}%</span>
            </button>
            <p v-if="!analysis.length" class="py-6 text-center text-sm text-slate-400">暂无可分析数据</p>
          </div>

          <!-- 饼状 -->
          <div v-else class="mt-4">
            <svg viewBox="0 0 200 200" class="mx-auto h-52 w-52">
              <path
                v-for="(s, i) in pieSlices"
                :key="i"
                :d="s.d"
                :fill="s.color"
                :opacity="s.selected ? 1 : 0.9"
                :stroke="s.selected ? '#1e293b' : 'white'"
                :stroke-width="s.selected ? 2 : 1"
                class="cursor-pointer transition-opacity hover:opacity-100"
                @click="drill(groupBy, s.label)"
              />
              <text x="100" y="96" text-anchor="middle" class="fill-slate-400" style="font-size: 11px">合计</text>
              <text x="100" y="114" text-anchor="middle" class="fill-slate-700" style="font-size: 18px; font-weight: 700">
                {{ chartRows.length }}
              </text>
            </svg>
            <div class="mt-3 space-y-1.5">
              <button
                v-for="item in analysis"
                :key="item.label"
                class="flex w-full items-center gap-2 rounded-lg px-2 py-1 text-left text-sm transition"
                :class="item.selected ? 'bg-indigo-50' : 'hover:bg-slate-50'"
                @click="drill(groupBy, item.label)"
              >
                <span class="h-3 w-3 shrink-0 rounded-sm" :style="{ background: item.color }" />
                <span class="flex-1 truncate text-slate-600">{{ item.display }}</span>
                <span class="text-xs text-slate-400">{{ item.value }} · {{ item.rowPct }}%</span>
              </button>
            </div>
          </div>
          <p class="mt-3 text-center text-xs text-slate-400">点击分区可按该值下钻筛选</p>
        </div>

        <!-- 右:卡片面板(按维度分组) -->
        <div class="lg:col-span-3">
          <div class="flex flex-wrap items-center gap-3">
            <span class="text-sm font-semibold text-slate-700">数据面板</span>
            <label class="flex items-center gap-2 text-sm text-slate-600">
              维度
              <select v-model="dimension" class="rounded-lg border border-slate-200 px-2 py-1.5 text-sm">
                <option value="">（不分组）</option>
                <option v-for="f in fields" :key="f.id" :value="f.name">{{ f.name }}</option>
              </select>
            </label>
            <span class="text-xs text-slate-400">共 {{ filteredRows.length }} 条 · {{ groups.length }} 组</span>
          </div>

          <div
            v-if="!filteredRows.length"
            class="mt-6 rounded-2xl border border-dashed border-slate-200 bg-white px-6 py-16 text-center text-slate-400"
          >
            无匹配数据
          </div>

          <div v-else class="mt-4 space-y-6">
            <div v-for="g in groups" :key="g.key">
              <div class="mb-2 flex items-center gap-2">
                <span class="rounded-lg bg-slate-800 px-2.5 py-1 text-xs font-medium text-white">{{ g.label }}</span>
                <span class="text-xs text-slate-400">{{ g.rows.length }} 条</span>
              </div>
              <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
                <button
                  v-for="row in g.rows"
                  :key="String(row.id)"
                  class="group relative flex flex-col gap-2 rounded-2xl border border-slate-200 bg-white p-4 text-left shadow-sm transition duration-200 hover:z-10 hover:-translate-y-0.5 hover:scale-[1.04] hover:border-indigo-300 hover:shadow-xl"
                  @click="openDetail(row)"
                >
                  <p class="truncate text-base font-semibold text-slate-800">
                    {{ cellLabel(titleField, row[titleField?.name || '']) || '未命名' }}
                  </p>
                  <div class="space-y-1">
                    <p v-for="f in previewFields" :key="f.id" class="flex items-center gap-1.5 text-xs">
                      <span class="shrink-0 text-slate-400">{{ f.name }}</span>
                      <span class="truncate text-slate-600">{{ cellLabel(f, row[f.name]) || '—' }}</span>
                    </p>
                  </div>
                  <span class="mt-1 text-[11px] text-indigo-500 opacity-0 transition group-hover:opacity-100">
                    查看详情 →
                  </span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- 筛选/跳转阶段:保留左侧数据源树 -->
    <div v-else class="mt-6 grid gap-6 lg:grid-cols-4">
      <div class="rounded-2xl border border-slate-200 bg-white p-4 lg:col-span-1">
        <p class="mb-2 px-2 text-sm font-semibold text-slate-700">数据源</p>
        <div v-if="!datasets.length" class="rounded-lg bg-amber-50 px-3 py-3 text-xs text-amber-700">
          <p class="font-medium">暂无可用的数据源</p>
          <p class="mt-1">{{ status?.error || '请在「数据源」页配置 Baserow。' }}</p>
        </div>
        <div v-else class="space-y-3">
          <div v-for="ws in tree" :key="ws.workspace">
            <p class="px-2 text-xs font-semibold uppercase tracking-wide text-slate-400">{{ ws.workspace }}</p>
            <div v-for="db in ws.databases" :key="db.database" class="mt-1">
              <p class="px-2 py-0.5 text-xs text-slate-500">{{ db.database }}</p>
              <ul>
                <li v-for="t in db.tables" :key="t.key">
                  <button
                    class="flex w-full items-center rounded-lg px-3 py-1.5 text-left text-sm transition"
                    :class="activeKey === t.key ? 'bg-indigo-50 text-indigo-700' : 'text-slate-600 hover:bg-slate-50'"
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

      <div class="space-y-6 lg:col-span-3">
        <div v-if="!activeDataset" class="rounded-2xl border border-slate-200 bg-white px-6 py-16 text-center text-slate-400">
          请选择左侧的数据表
        </div>

        <div v-else-if="stage === 'filter'" class="rounded-2xl border border-slate-200 bg-white p-6">
          <p class="font-semibold text-slate-800">选择筛选条件</p>
          <p class="mt-0.5 text-xs text-slate-400">点击列名标签进行选择(可多选组合),再为每个条件选择值</p>

          <div class="mt-4 flex flex-wrap gap-2">
            <button
              v-for="f in fields"
              :key="f.id"
              class="rounded-full px-3 py-1.5 text-sm font-medium ring-1 transition"
              :class="
                selectedFields.includes(f.name)
                  ? 'bg-indigo-500 text-white ring-indigo-500'
                  : 'bg-white text-slate-600 ring-slate-200 hover:bg-slate-50'
              "
              @click="toggleField(f.name)"
            >
              {{ f.name }}
            </button>
          </div>

          <div v-if="selectedFields.length" class="mt-6 space-y-3">
            <div v-for="name in selectedFields" :key="name" class="flex items-center gap-3">
              <span class="w-28 shrink-0 truncate text-sm text-slate-600">{{ name }}</span>
              <select v-model="filters[name]" class="w-full max-w-xs rounded-lg border border-slate-200 px-3 py-2 text-sm">
                <option value="">（选择值）</option>
                <option v-for="v in valueOptions(name)" :key="v" :value="v">{{ v }}</option>
              </select>
            </div>
          </div>
          <p v-else class="mt-6 text-sm text-slate-400">尚未选择任何条件,可直接进入查看全部数据</p>

          <div class="mt-6 flex items-center gap-3">
            <button class="rounded-lg bg-indigo-500 px-5 py-2 text-sm font-medium text-white hover:bg-indigo-600" @click="confirmFilters">
              确认筛选
            </button>
            <button class="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600" @click="selectedFields = []; filters = {}">
              清空
            </button>
          </div>
        </div>

        <div v-else class="rounded-2xl border border-slate-200 bg-white p-6">
          <p class="font-semibold text-slate-800">筛选结果预览</p>
          <p class="mt-0.5 text-xs text-slate-400">表「{{ activeDataset.table }}」· 总 {{ totalLoaded }} 条</p>

          <div v-if="jumpRows.length" class="mt-4 space-y-2">
            <div
              v-for="j in jumpRows"
              :key="j.field"
              class="flex items-center justify-between rounded-xl border border-slate-100 px-4 py-3"
            >
              <p class="text-sm text-slate-600">
                <span class="font-medium text-slate-700">{{ j.field }}</span> = {{ j.value || '（空）' }}
              </p>
              <div class="text-right">
                <p class="text-lg font-bold text-indigo-600">{{ j.count }}</p>
                <p class="text-xs text-slate-400">占比 {{ j.pct }}%</p>
              </div>
            </div>
            <div class="flex items-center justify-between rounded-xl bg-indigo-50 px-4 py-3">
              <p class="text-sm font-medium text-indigo-700">组合筛选命中</p>
              <div class="text-right">
                <p class="text-lg font-bold text-indigo-700">{{ filteredRows.length }}</p>
                <p class="text-xs text-indigo-400">
                  占比 {{ totalLoaded ? Math.round((filteredRows.length / totalLoaded) * 100) : 0 }}%
                </p>
              </div>
            </div>
          </div>
          <p v-else class="mt-4 text-sm text-slate-400">未设置筛选条件,将展示全部数据</p>

          <div class="mt-6 flex items-center gap-3">
            <button
              class="rounded-lg bg-gradient-to-r from-indigo-500 to-cyan-500 px-5 py-2 text-sm font-medium text-white shadow hover:opacity-90"
              @click="enterDisplay"
            >
              进入数据展示 →
            </button>
            <button class="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600" @click="stage = 'filter'">
              返回调整
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 详情大面板 -->
    <div
      v-if="detailRow"
      class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 backdrop-blur-sm"
      @click.self="closeDetail"
    >
      <div class="max-h-[88vh] w-full max-w-3xl overflow-y-auto rounded-2xl bg-white p-6 shadow-2xl">
        <div class="flex items-start justify-between gap-4">
          <div>
            <h2 class="text-xl font-bold text-slate-800">
              {{ cellLabel(titleField, detailRow[titleField?.name || '']) || '记录详情' }}
            </h2>
            <p class="mt-0.5 text-xs text-slate-400">完整数据信息</p>
          </div>
          <button class="text-slate-400 hover:text-slate-600" @click="closeDetail">✕</button>
        </div>

        <div class="mt-5 grid gap-3 sm:grid-cols-2">
          <div v-for="f in fields" :key="f.id" class="rounded-xl border border-slate-100 bg-slate-50/40 p-3">
            <p class="text-xs font-medium text-slate-400">{{ f.name }}</p>
            <div class="mt-1 text-sm text-slate-700">
              <template v-if="detailEdit && isEditable(f)">
                <select
                  v-if="f.type === 'single_select'"
                  v-model="detailForm[f.name]"
                  class="w-full rounded-lg border border-slate-200 px-2 py-1.5 text-sm"
                >
                  <option value="">（空）</option>
                  <option v-for="o in f.select_options" :key="o.id" :value="o.id">{{ o.value }}</option>
                </select>
                <div v-else-if="f.type === 'multiple_select'" class="flex flex-wrap gap-2">
                  <label
                    v-for="o in f.select_options"
                    :key="o.id"
                    class="flex cursor-pointer items-center gap-1.5 rounded-full border border-slate-200 px-2.5 py-1 text-xs text-slate-600 hover:bg-white"
                  >
                    <input
                      type="checkbox"
                      :value="o.id"
                      v-model="detailForm[f.name]"
                      class="h-3.5 w-3.5 accent-indigo-500"
                    />
                    {{ o.value }}
                  </label>
                </div>
                <input
                  v-else-if="f.type === 'boolean'"
                  v-model="detailForm[f.name]"
                  type="checkbox"
                  class="h-4 w-4 accent-indigo-500"
                />
                <input
                  v-else-if="f.type === 'number'"
                  v-model="detailForm[f.name]"
                  type="number"
                  class="w-full rounded-lg border border-slate-200 px-2 py-1.5 text-sm"
                />
                <input
                  v-else
                  v-model="detailForm[f.name]"
                  type="text"
                  class="w-full rounded-lg border border-slate-200 px-2 py-1.5 text-sm"
                />
              </template>
              <template v-else>
                <span
                  v-if="f.type === 'single_select' || f.type === 'multiple_select'"
                  class="inline-flex flex-wrap gap-1"
                >
                  <span
                    v-for="(p, pi) in pills(f, detailRow[f.name])"
                    :key="pi"
                    class="rounded-full px-2 py-0.5 text-xs font-medium"
                    :style="{ background: p.color + '22', color: p.color }"
                  >
                    {{ p.value }}
                  </span>
                  <span v-if="!pills(f, detailRow[f.name]).length" class="text-slate-300">—</span>
                </span>
                <span v-else-if="f.type === 'boolean'">{{ detailRow[f.name] ? '✓ 是' : '— 否' }}</span>
                <span v-else>{{ cellLabel(f, detailRow[f.name]) || '—' }}</span>
              </template>
            </div>
          </div>
        </div>

        <div class="mt-6 flex items-center gap-3">
          <template v-if="detailEdit">
            <button
              class="rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-600 disabled:opacity-50"
              :disabled="detailSaving"
              @click="saveDetail"
            >
              {{ detailSaving ? '保存中...' : '保存' }}
            </button>
            <button class="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600" @click="detailEdit = false">
              取消
            </button>
          </template>
          <template v-else>
            <button
              v-if="canEdit"
              class="rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-600"
              @click="startDetailEdit"
            >
              编辑
            </button>
            <button
              v-if="canDelete"
              class="rounded-lg border border-red-200 px-4 py-2 text-sm text-red-500 hover:bg-red-50"
              @click="removeRow(detailRow)"
            >
              删除
            </button>
            <button class="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600" @click="closeDetail">
              关闭
            </button>
          </template>
          <span v-if="detailMsg" class="text-sm text-red-500">{{ detailMsg }}</span>
        </div>
      </div>
    </div>

    <!-- 新增弹层 -->
    <div v-if="showEditor" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4" @click.self="showEditor = false">
      <div class="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-white p-6 shadow-xl">
        <div class="flex items-center justify-between">
          <h2 class="text-lg font-bold text-slate-800">新增数据</h2>
          <button class="text-slate-400 hover:text-slate-600" @click="showEditor = false">✕</button>
        </div>
        <div class="mt-5 space-y-4">
          <label v-for="f in editableFields" :key="f.id" class="block">
            <span class="mb-1 block text-sm text-slate-600">{{ f.name }}</span>
            <select v-if="f.type === 'single_select'" v-model="form[f.name]" class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm">
              <option value="">（空）</option>
              <option v-for="o in f.select_options" :key="o.id" :value="o.id">{{ o.value }}</option>
            </select>
            <div v-else-if="f.type === 'multiple_select'" class="flex flex-wrap gap-2">
              <label
                v-for="o in f.select_options"
                :key="o.id"
                class="flex cursor-pointer items-center gap-1.5 rounded-full border border-slate-200 px-2.5 py-1 text-xs text-slate-600 hover:bg-slate-50"
              >
                <input type="checkbox" :value="o.id" v-model="form[f.name]" class="h-3.5 w-3.5 accent-indigo-500" />
                {{ o.value }}
              </label>
            </div>
            <input v-else-if="f.type === 'boolean'" v-model="form[f.name]" type="checkbox" class="h-4 w-4 accent-indigo-500" />
            <input v-else-if="f.type === 'number'" v-model="form[f.name]" type="number" class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm" />
            <input v-else-if="f.type === 'date'" v-model="form[f.name]" type="date" class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm" />
            <input v-else v-model="form[f.name]" type="text" class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm" />
          </label>
        </div>
        <div class="mt-6 flex items-center gap-3">
          <button class="rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-600 disabled:opacity-50" :disabled="saving" @click="save">
            {{ saving ? '保存中...' : '保存' }}
          </button>
          <span v-if="editorMsg" class="text-sm text-red-500">{{ editorMsg }}</span>
        </div>
      </div>
    </div>
  </AppLayout>
</template>
