<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppLayout from '../components/AppLayout.vue'
import * as dtApi from '../api/datatables'
import type { DataField, DataRecord, DataTable } from '../api/datatables'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const tables = ref<DataTable[]>([])
const activeCode = ref('')
const rows = ref<DataRecord[]>([])
const search = ref('')
const loading = ref(false)
const error = ref('')

const activeTable = computed(() => tables.value.find((t) => t.code === activeCode.value))
const fields = computed<DataField[]>(() => activeTable.value?.fields ?? [])
const titleField = computed<DataField | undefined>(() => {
  const key = activeTable.value?.title_field
  return fields.value.find((f) => f.key === key) ?? fields.value[0]
})

const canCreate = computed(() => auth.hasPermission('data:create'))
const canEdit = computed(() => auth.hasPermission('data:edit'))
const canDelete = computed(() => auth.hasPermission('data:delete'))

function optionColor(field: DataField, value: string): string {
  return field.options.find((o) => o.value === value)?.color || '#eef2ff'
}

function selectValues(field: DataField, value: unknown): string[] {
  if (field.type === 'multiple_select') return Array.isArray(value) ? value.map(String) : []
  if (value === null || value === undefined || value === '') return []
  return [String(value)]
}

function cellText(field: DataField, value: unknown): string {
  if (value === null || value === undefined || value === '') return ''
  if (field.type === 'boolean') return value ? '是' : '否'
  if (field.type === 'multiple_select' && Array.isArray(value)) return value.join('、')
  return String(value)
}

function recordTitle(record: DataRecord): string {
  const f = titleField.value
  if (!f) return `#${record.id}`
  return cellText(f, record.data[f.key]) || `#${record.id}`
}

function openPanel() {
  const table = activeTable.value
  if (table) router.push(`/department/data/${table.code}`)
}

async function loadTables() {
  loading.value = true
  error.value = ''
  try {
    tables.value = await dtApi.listTables()
    const wanted = String(route.query.table || '')
    if (wanted && tables.value.some((t) => t.code === wanted)) activeCode.value = wanted
    else if (!activeCode.value && tables.value.length) activeCode.value = tables.value[0].code
  } catch (err: unknown) {
    error.value =
      (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '加载数据表失败'
  } finally {
    loading.value = false
  }
}

async function loadRows() {
  if (!activeCode.value) {
    rows.value = []
    return
  }
  loading.value = true
  error.value = ''
  try {
    rows.value = await dtApi.listRecords(activeCode.value, search.value.trim() || undefined)
  } catch (err: unknown) {
    error.value =
      (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '加载记录失败'
    rows.value = []
  } finally {
    loading.value = false
  }
}

watch(activeCode, () => {
  search.value = ''
  void loadRows()
})

onMounted(async () => {
  if (!auth.user) await auth.loadUser()
  await loadTables()
  await loadRows()
})

// ---- 新增 / 编辑 ----
const showEditor = ref(false)
const editingRecord = ref<DataRecord | null>(null)
const form = ref<Record<string, any>>({})
const saving = ref(false)
const formError = ref('')

function emptyValue(field: DataField): unknown {
  if (field.type === 'boolean') return false
  if (field.type === 'multiple_select') return []
  return ''
}

function openCreate() {
  editingRecord.value = null
  formError.value = ''
  const init: Record<string, unknown> = {}
  for (const f of fields.value) init[f.key] = emptyValue(f)
  form.value = init
  showEditor.value = true
}

function openEdit(record: DataRecord) {
  editingRecord.value = record
  formError.value = ''
  const init: Record<string, unknown> = {}
  for (const f of fields.value) {
    const v = record.data[f.key]
    if (f.type === 'boolean') init[f.key] = Boolean(v)
    else if (f.type === 'multiple_select') init[f.key] = Array.isArray(v) ? v.map(String) : []
    else if (v === null || v === undefined) init[f.key] = ''
    else init[f.key] = v
  }
  form.value = init
  showEditor.value = true
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

async function save() {
  const table = activeTable.value
  if (!table) return
  const values: Record<string, unknown> = {}
  for (const f of fields.value) {
    const v = normalize(f, form.value[f.key])
    if (f.required && (v === null || v === '' || (Array.isArray(v) && !v.length))) {
      formError.value = `请填写必填字段「${f.label}」`
      return
    }
    values[f.key] = v
  }
  saving.value = true
  formError.value = ''
  try {
    if (editingRecord.value) {
      await dtApi.updateRecord(table.code, editingRecord.value.id, values)
    } else {
      await dtApi.createRecord(table.code, values)
    }
    showEditor.value = false
    await loadRows()
  } catch (err: unknown) {
    formError.value =
      (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '保存失败'
  } finally {
    saving.value = false
  }
}

// ---- 详情 ----
const detail = ref<DataRecord | null>(null)

function openDetail(record: DataRecord) {
  detail.value = record
}

async function remove(record: DataRecord) {
  const table = activeTable.value
  if (!table) return
  if (!confirm('确认删除该记录?')) return
  try {
    await dtApi.deleteRecord(table.code, record.id)
    detail.value = null
    await loadRows()
  } catch (err: unknown) {
    alert((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '删除失败')
  }
}
</script>

<template>
  <AppLayout wide>
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-slate-800">数据看板</h1>
        <p class="mt-1 text-sm text-slate-500">
          <template v-if="activeTable">
            {{ activeTable.name }}
            <span class="ml-2 font-mono text-xs text-slate-400">{{ activeTable.code }}</span>
            · 共 {{ rows.length }} 条
          </template>
          <template v-else>暂无可用数据表</template>
        </p>
      </div>
      <div class="flex items-center gap-2">
        <input
          v-model="search"
          placeholder="搜索记录"
          class="rounded-lg border border-slate-200 px-3 py-2 text-sm"
          @keyup.enter="loadRows"
        />
        <button
          class="rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50"
          @click="loadRows"
        >
          搜索
        </button>
      </div>
    </div>

    <p v-if="error" class="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-500">{{ error }}</p>

    <div class="mt-6 grid gap-6 lg:grid-cols-4">
      <aside class="rounded-2xl border border-slate-200 bg-white p-4 lg:col-span-1">
        <p class="mb-2 px-2 text-sm font-semibold text-slate-700">数据表</p>
        <div v-if="!tables.length" class="rounded-lg bg-amber-50 px-3 py-3 text-xs text-amber-700">
          <p class="font-medium">暂无数据表</p>
          <p v-if="auth.isAdmin" class="mt-1">
            请到「数据表管理」创建。或先到
            <RouterLink to="/admin/datatables" class="underline">数据表管理</RouterLink>
          </p>
        </div>
        <ul v-else class="space-y-0.5">
          <li v-for="t in tables" :key="t.id">
            <button
              class="flex w-full items-start justify-between gap-2 rounded-lg px-3 py-2 text-left transition"
              :class="activeCode === t.code ? 'bg-indigo-50 text-indigo-700' : 'text-slate-600 hover:bg-slate-50'"
              @click="activeCode = t.code"
            >
              <span class="min-w-0">
                <span class="block truncate text-sm font-medium">{{ t.name }}</span>
                <span class="block truncate font-mono text-[11px] text-slate-400">{{ t.code }}</span>
              </span>
              <span class="shrink-0 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-500">
                {{ t.fields.length }}
              </span>
            </button>
          </li>
        </ul>
      </aside>

      <section class="lg:col-span-3">
        <div v-if="!activeTable" class="rounded-2xl border border-slate-200 bg-white px-6 py-16 text-center text-slate-400">
          请选择左侧数据表
        </div>
        <div v-else class="overflow-hidden rounded-2xl border border-slate-200 bg-white">
          <div class="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 px-5 py-3">
            <div class="min-w-0">
              <p class="truncate text-sm font-semibold text-slate-800">{{ activeTable.name }}</p>
              <p class="truncate text-xs text-slate-400">{{ activeTable.description || '—' }}</p>
            </div>
            <div class="ml-auto flex items-center gap-2">
              <span class="text-xs text-slate-400">{{ rows.length }} 条记录</span>
              <button
                class="rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
                @click="openPanel"
              >
                面板视图
              </button>
              <button
                v-if="canCreate"
                class="rounded-lg bg-indigo-500 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-600"
                @click="openCreate"
              >
                新增
              </button>
            </div>
          </div>

          <div v-if="loading" class="px-5 py-10 text-center text-sm text-slate-400">加载中...</div>
          <div v-else-if="!rows.length" class="px-5 py-16 text-center text-sm text-slate-400">
            暂无数据{{ search ? '(无匹配结果)' : '' }}
          </div>
          <div v-else class="overflow-x-auto">
            <table class="w-full min-w-[640px] text-sm">
              <thead class="bg-slate-50 text-left text-xs text-slate-400">
                <tr>
                  <th v-for="f in fields" :key="f.id" class="whitespace-nowrap px-4 py-2.5 font-medium">
                    {{ f.label }}
                    <span v-if="f.required" class="text-red-400">*</span>
                  </th>
                  <th class="px-4 py-2.5 font-medium">归属</th>
                  <th class="px-4 py-2.5"></th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100">
                <tr
                  v-for="r in rows"
                  :key="r.id"
                  class="cursor-pointer transition hover:bg-slate-50"
                  @click="openDetail(r)"
                >
                  <td v-for="f in fields" :key="f.id" class="max-w-[240px] px-4 py-2.5">
                    <template v-if="f.type === 'single_select' || f.type === 'multiple_select'">
                      <span class="inline-flex flex-wrap gap-1">
                        <span
                          v-for="v in selectValues(f, r.data[f.key])"
                          :key="v"
                          class="rounded-full px-2 py-0.5 text-[11px] text-slate-700"
                          :style="{ background: optionColor(f, v) }"
                        >
                          {{ v }}
                        </span>
                        <span v-if="!selectValues(f, r.data[f.key]).length" class="text-slate-300">—</span>
                      </span>
                    </template>
                    <template v-else-if="f.type === 'boolean'">
                      <span
                        class="rounded-full px-2 py-0.5 text-[11px]"
                        :class="r.data[f.key] ? 'bg-emerald-50 text-emerald-600' : 'bg-slate-100 text-slate-400'"
                      >
                        {{ r.data[f.key] ? '是' : '否' }}
                      </span>
                    </template>
                    <template v-else>
                      <span class="block truncate text-slate-700" :title="cellText(f, r.data[f.key])">
                        {{ cellText(f, r.data[f.key]) || '—' }}
                      </span>
                    </template>
                  </td>
                  <td class="whitespace-nowrap px-4 py-2.5 text-xs text-slate-400">
                    {{ r.department || '—' }}
                  </td>
                  <td class="whitespace-nowrap px-4 py-2.5 text-right text-xs text-indigo-500">详情 →</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>

    <!-- 详情 -->
    <Teleport to="body">
    <div
      v-if="detail"
      class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4"
      @click.self="detail = null"
    >
      <div class="max-h-[88vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white p-6 shadow-2xl">
        <div class="flex items-start justify-between gap-4">
          <div class="min-w-0">
            <h2 class="truncate text-xl font-bold text-slate-800">{{ recordTitle(detail) }}</h2>
            <p class="mt-0.5 text-xs text-slate-400">
              {{ detail.department || '未设置部门' }} · 创建者 {{ detail.owner_username }}
            </p>
          </div>
          <button class="text-slate-400 hover:text-slate-600" @click="detail = null">✕</button>
        </div>

        <div class="mt-5 grid gap-3 sm:grid-cols-2">
          <div v-for="f in fields" :key="f.id" class="rounded-xl border border-slate-100 bg-slate-50/40 p-3">
            <p class="text-xs font-medium text-slate-400">{{ f.label }}</p>
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

        <p class="mt-4 text-xs text-slate-400">
          创建 {{ new Date(detail.created_at).toLocaleString() }} · 更新
          {{ new Date(detail.updated_at).toLocaleString() }}
        </p>

        <div class="mt-6 flex items-center gap-3">
          <button
            v-if="canEdit"
            class="rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-600"
            @click="openEdit(detail)"
          >
            编辑
          </button>
          <button
            v-if="canDelete"
            class="rounded-lg border border-red-200 px-4 py-2 text-sm text-red-500 hover:bg-red-50"
            @click="remove(detail)"
          >
            删除
          </button>
          <button class="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600" @click="detail = null">
            关闭
          </button>
        </div>
      </div>
    </div>

    <!-- 新增 / 编辑 -->
    <div
      v-if="showEditor"
      class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4"
      @click.self="showEditor = false"
    >
      <div class="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-white p-6 shadow-xl">
        <div class="flex items-center justify-between">
          <h2 class="text-lg font-bold text-slate-800">{{ editingRecord ? '编辑记录' : '新增记录' }}</h2>
          <button class="text-slate-400 hover:text-slate-600" @click="showEditor = false">✕</button>
        </div>
        <div class="mt-5 space-y-4">
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
                  type="checkbox"
                  :value="o.value"
                  v-model="form[f.key]"
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
          <p v-if="!fields.length" class="text-sm text-slate-400">该表还没有字段,请先在数据表管理中配置。</p>
        </div>
        <div class="mt-6 flex items-center gap-3">
          <button
            class="rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-600 disabled:opacity-50"
            :disabled="saving"
            @click="save"
          >
            {{ saving ? '保存中...' : '保存' }}
          </button>
          <span v-if="formError" class="text-sm text-red-500">{{ formError }}</span>
        </div>
      </div>
    </div>
    </Teleport>
  </AppLayout>
</template>
