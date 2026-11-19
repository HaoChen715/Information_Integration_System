<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppLayout from '../components/AppLayout.vue'
import * as dtApi from '../api/datatables'
import type { DataField, DataRecord, DataTable } from '../api/datatables'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const code = computed(() => String(route.params.code || ''))
const table = ref<DataTable | null>(null)
const rows = ref<DataRecord[]>([])
const loading = ref(false)
const error = ref('')
const search = ref('')
const groupBy = ref('')
const filters = ref<Record<string, string>>({})
const detail = ref<DataRecord | null>(null)
const modalOpen = ref(false)
const editing = ref(false)
const form = ref<Record<string, any>>({})
const saving = ref(false)
const formError = ref('')

const canCreate = computed(() => auth.hasPermission('data:create'))
const canEdit = computed(() => auth.hasPermission('data:edit'))
const canDelete = computed(() => auth.hasPermission('data:delete'))

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

function initForm(values?: Record<string, unknown>) {
  const init: Record<string, any> = {}
  for (const field of fields.value) {
    const value = values?.[field.key]
    if (field.type === 'boolean') init[field.key] = Boolean(value)
    else if (field.type === 'multiple_select') init[field.key] = Array.isArray(value) ? value.map(String) : []
    else init[field.key] = value ?? ''
  }
  form.value = init
}

function openDetail(row: DataRecord) {
  detail.value = row
  editing.value = false
  formError.value = ''
  modalOpen.value = true
}

function startCreate() {
  detail.value = null
  editing.value = true
  formError.value = ''
  initForm()
  modalOpen.value = true
}

function startEdit() {
  if (!detail.value) return
  editing.value = true
  formError.value = ''
  initForm(detail.value.data)
}

function cancelEdit() {
  formError.value = ''
  if (detail.value) editing.value = false
  else closeModal()
}

function closeModal() {
  modalOpen.value = false
  editing.value = false
  detail.value = null
  formError.value = ''
}

function normalize(field: DataField, value: unknown): unknown {
  if (field.type === 'multiple_select') return Array.isArray(value) ? value : []
  if (field.type === 'boolean') return Boolean(value)
  if (value === '' || value === null || value === undefined) return null
  if (field.type === 'number') {
    const n = Number(value)
    return Number.isNaN(n) ? null : n
  }
  return value
}

async function saveRecord() {
  const values: Record<string, unknown> = {}
  for (const field of fields.value) {
    const value = normalize(field, form.value[field.key])
    if (field.required && (value === null || value === '' || (Array.isArray(value) && !value.length))) {
      formError.value = `请填写必填字段「${field.label}」`
      return
    }
    values[field.key] = value
  }
  saving.value = true
  formError.value = ''
  try {
    if (detail.value) {
      const updated = await dtApi.updateRecord(code.value, detail.value.id, values)
      detail.value = updated
      await loadRows()
      const found = rows.value.find((r) => r.id === updated.id)
      if (found) detail.value = found
      editing.value = false
    } else {
      await dtApi.createRecord(code.value, values)
      await loadRows()
      closeModal()
    }
  } catch (err: unknown) {
    formError.value =
      (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '保存失败'
  } finally {
    saving.value = false
  }
}

async function removeRecord(row: DataRecord) {
  if (!confirm('确认删除该记录?')) return
  try {
    await dtApi.deleteRecord(code.value, row.id)
    closeModal()
    await loadRows()
  } catch (err: unknown) {
    alert((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '删除失败')
  }
}

function removeCurrent() {
  if (detail.value) void removeRecord(detail.value)
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
      <div class="flex items-center gap-2">
        <button
          v-if="canCreate"
          class="rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-600"
          @click="startCreate"
        >
          新增
        </button>
        <button
          class="rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50"
          @click="backToTable"
        >
          表格视图
        </button>
      </div>
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
      v-if="modalOpen"
      class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 backdrop-blur-sm"
      @click.self="closeModal"
    >
      <div class="modal-in max-h-[88vh] w-full max-w-5xl overflow-y-auto rounded-2xl bg-white p-6 shadow-2xl">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <h2 class="truncate text-xl font-bold text-slate-800">
              {{ detail ? recordTitle(detail) : '新增记录' }}
            </h2>
            <p class="mt-0.5 text-xs text-slate-400">
              {{ detail ? `${detail.department || '未设置部门'} · ${detail.owner_username}` : table?.name }}
            </p>
          </div>
          <button class="text-slate-400 hover:text-slate-600" @click="closeModal">✕</button>
        </div>

        <div v-if="!editing && detail" class="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          <div v-for="f in fields" :key="f.id" class="rounded-xl border border-slate-100 bg-slate-50/50 px-3 py-2.5">
            <p class="text-[11px] text-slate-400">{{ f.label }}</p>
            <div class="mt-1 text-sm text-slate-700">
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

        <div v-else class="mt-5 grid gap-4 sm:grid-cols-2">
          <label v-for="f in fields" :key="f.id" class="block">
            <span class="mb-1 block text-sm text-slate-600">
              {{ f.label }} <span v-if="f.required" class="text-red-400">*</span>
            </span>
            <select
              v-if="f.type === 'single_select'"
              v-model="form[f.key]"
              class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            >
              <option value="">（空）</option>
              <option v-for="o in f.options" :key="o.value" :value="o.value">{{ o.value }}</option>
            </select>
            <div v-else-if="f.type === 'multiple_select'" class="flex flex-wrap gap-2">
              <label
                v-for="o in f.options"
                :key="o.value"
                class="flex cursor-pointer items-center gap-1.5 rounded-full border border-slate-200 px-2.5 py-1 text-xs text-slate-600 hover:bg-slate-50"
              >
                <input
                  v-model="form[f.key]"
                  type="checkbox"
                  :value="o.value"
                  class="h-3.5 w-3.5 accent-indigo-500"
                />
                {{ o.value }}
              </label>
            </div>
            <label v-else-if="f.type === 'boolean'" class="flex items-center gap-2 text-sm text-slate-600">
              <input v-model="form[f.key]" type="checkbox" class="h-4 w-4 accent-indigo-500" />
              是
            </label>
            <input
              v-else-if="f.type === 'number'"
              v-model="form[f.key]"
              type="number"
              class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            />
            <input
              v-else-if="f.type === 'date'"
              v-model="form[f.key]"
              type="date"
              class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            />
            <textarea
              v-else-if="f.type === 'long_text'"
              v-model="form[f.key]"
              rows="3"
              class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            />
            <input
              v-else
              v-model="form[f.key]"
              type="text"
              class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            />
          </label>
          <p v-if="!fields.length" class="text-sm text-slate-400">该表还没有字段。</p>
        </div>

        <p v-if="detail" class="mt-4 text-[11px] text-slate-400">
          创建 {{ new Date(detail.created_at).toLocaleString() }} · 更新 {{ new Date(detail.updated_at).toLocaleString() }}
        </p>

        <div class="mt-5 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-4">
          <template v-if="editing">
            <button
              class="rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-600 disabled:opacity-50"
              :disabled="saving"
              @click="saveRecord"
            >
              {{ saving ? '保存中...' : '保存' }}
            </button>
            <button class="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600" @click="cancelEdit">
              取消
            </button>
            <span v-if="formError" class="text-sm text-red-500">{{ formError }}</span>
          </template>
          <template v-else>
            <button
              v-if="canEdit && detail"
              class="rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-600"
              @click="startEdit"
            >
              编辑
            </button>
            <button
              v-if="canDelete && detail"
              class="rounded-lg border border-red-200 px-4 py-2 text-sm text-red-500 hover:bg-red-50"
              @click="removeCurrent"
            >
              删除
            </button>
            <button class="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600" @click="closeModal">
              关闭
            </button>
          </template>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<style scoped>
@keyframes modal-in {
  from {
    opacity: 0;
    transform: translateY(14px) scale(0.97);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}
.modal-in {
  animation: modal-in 0.18s ease-out;
}
</style>
