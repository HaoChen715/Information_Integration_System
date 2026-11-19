<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import AppLayout from '../../components/AppLayout.vue'
import * as dtApi from '../../api/datatables'
import type { DataTable, FieldOption, TablePayload } from '../../api/datatables'

const FIELD_TYPES = [
  { value: 'text', label: '单行文本' },
  { value: 'long_text', label: '多行文本' },
  { value: 'number', label: '数字' },
  { value: 'date', label: '日期' },
  { value: 'boolean', label: '是 / 否' },
  { value: 'single_select', label: '单选' },
  { value: 'multiple_select', label: '多选' },
]

const OPTION_COLORS = [
  '#e0e7ff',
  '#dcfce7',
  '#fef3c7',
  '#fee2e2',
  '#cffafe',
  '#f3e8ff',
  '#f1f5f9',
  '#fce7f3',
]

interface FieldDraft {
  key: string
  label: string
  type: string
  required: boolean
  optionsText: string
}

const tables = ref<DataTable[]>([])
const loading = ref(false)
const error = ref('')

const showEditor = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const saveError = ref('')

const form = ref({
  code: '',
  name: '',
  description: '',
  title_field: '',
  scope_by_department: true,
  department_field: '',
  fields: [] as FieldDraft[],
})

const isEditing = computed(() => editingId.value !== null)
const fieldKeyOptions = computed(() =>
  form.value.fields.filter((f) => f.key.trim()).map((f) => ({ key: f.key.trim(), label: f.label || f.key })),
)

function needsOptions(type: string): boolean {
  return type === 'single_select' || type === 'multiple_select'
}

function parseOptions(text: string): FieldOption[] {
  const seen = new Set<string>()
  const out: FieldOption[] = []
  for (const raw of text.split(/[\n,，]/)) {
    const value = raw.trim()
    if (!value || seen.has(value)) continue
    seen.add(value)
    out.push({ value, color: OPTION_COLORS[out.length % OPTION_COLORS.length] })
  }
  return out
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    tables.value = await dtApi.listAdminTables()
  } catch (err: unknown) {
    error.value =
      (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '加载数据表失败'
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  saveError.value = ''
  form.value = {
    code: '',
    name: '',
    description: '',
    title_field: '',
    scope_by_department: true,
    department_field: '',
    fields: [],
  }
  addField()
  showEditor.value = true
}

function openEdit(table: DataTable) {
  editingId.value = table.id
  saveError.value = ''
  form.value = {
    code: table.code,
    name: table.name,
    description: table.description ?? '',
    title_field: table.title_field ?? '',
    scope_by_department: table.scope_by_department,
    department_field: table.department_field ?? '',
    fields: table.fields.map((f) => ({
      key: f.key,
      label: f.label,
      type: f.type,
      required: f.required,
      optionsText: (f.options ?? []).map((o) => o.value).join('\n'),
    })),
  }
  showEditor.value = true
}

function closeEditor() {
  showEditor.value = false
  saving.value = false
}

function addField() {
  form.value.fields.push({ key: '', label: '', type: 'text', required: false, optionsText: '' })
}

function removeField(index: number) {
  form.value.fields.splice(index, 1)
}

function moveField(index: number, delta: number) {
  const next = index + delta
  if (next < 0 || next >= form.value.fields.length) return
  const [item] = form.value.fields.splice(index, 1)
  form.value.fields.splice(next, 0, item)
}

function buildPayload(): TablePayload | null {
  saveError.value = ''
  if (!/^[a-z][a-z0-9_]{1,63}$/.test(form.value.code.trim())) {
    saveError.value = '表标识需以小写字母开头,仅含小写字母、数字、下划线,长度 2-64'
    return null
  }
  if (!form.value.name.trim()) {
    saveError.value = '请填写表名称'
    return null
  }
  const keys = new Set<string>()
  const fields = []
  for (const f of form.value.fields) {
    const key = f.key.trim()
    const label = f.label.trim()
    if (!key || !label) {
      saveError.value = '每个字段都需要填写标识和名称'
      return null
    }
    if (!/^[a-zA-Z][a-zA-Z0-9_]{0,63}$/.test(key)) {
      saveError.value = `字段标识「${key}」需以字母开头,仅含字母、数字、下划线`
      return null
    }
    if (keys.has(key)) {
      saveError.value = `字段标识「${key}」重复`
      return null
    }
    keys.add(key)
    fields.push({
      key,
      label,
      type: f.type,
      required: f.required,
      options: needsOptions(f.type) ? parseOptions(f.optionsText) : [],
    })
  }
  return {
    code: form.value.code.trim(),
    name: form.value.name.trim(),
    description: form.value.description.trim() || null,
    title_field: form.value.title_field,
    scope_by_department: form.value.scope_by_department,
    department_field: form.value.scope_by_department ? form.value.department_field : '',
    fields,
  }
}

async function save() {
  const payload = buildPayload()
  if (!payload) return
  saving.value = true
  saveError.value = ''
  try {
    if (editingId.value === null) {
      await dtApi.createTable(payload)
    } else {
      await dtApi.updateTable(editingId.value, payload)
    }
    showEditor.value = false
    await load()
  } catch (err: unknown) {
    saveError.value =
      (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '保存失败'
  } finally {
    saving.value = false
  }
}

async function remove(table: DataTable) {
  if (!confirm(`确认删除数据表「${table.name}」?该表所有记录将一并删除,不可恢复。`)) return
  try {
    await dtApi.deleteTable(table.id)
    await load()
  } catch (err: unknown) {
    alert((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '删除失败')
  }
}

onMounted(load)
</script>

<template>
  <AppLayout>
    <div class="flex items-start justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-slate-800">数据表管理</h1>
        <p class="mt-1 text-sm text-slate-500">
          在网页上定义数据表与字段,数据存储于系统自带数据库,不再依赖 Baserow。
        </p>
      </div>
      <button
        class="rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-600"
        @click="openCreate"
      >
        新增数据表
      </button>
    </div>

    <p v-if="error" class="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-500">{{ error }}</p>
    <p v-if="loading" class="mt-6 text-sm text-slate-400">加载中...</p>

    <div v-if="!loading && !tables.length" class="mt-6 rounded-2xl border border-dashed border-slate-200 bg-white px-6 py-16 text-center">
      <p class="text-slate-500">还没有数据表</p>
      <p class="mt-1 text-sm text-slate-400">点击右上角「新增数据表」开始定义</p>
    </div>

    <div v-else class="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      <div
        v-for="t in tables"
        :key="t.id"
        class="flex flex-col rounded-2xl border border-slate-200 bg-white p-5 transition hover:-translate-y-0.5 hover:border-indigo-200 hover:shadow-md"
      >
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <p class="truncate text-base font-semibold text-slate-800">{{ t.name }}</p>
            <p class="mt-0.5 truncate font-mono text-xs text-slate-400">{{ t.code }}</p>
          </div>
          <span
            class="shrink-0 rounded-full px-2 py-0.5 text-[11px]"
            :class="t.scope_by_department ? 'bg-sky-50 text-sky-600' : 'bg-slate-100 text-slate-500'"
          >
            {{ t.scope_by_department ? '按部门' : '公共表' }}
          </span>
        </div>
        <p class="mt-2 line-clamp-2 min-h-[2.5rem] text-sm text-slate-500">
          {{ t.description || '暂无描述' }}
        </p>
        <div class="mt-3 flex items-center gap-3 text-xs text-slate-400">
          <span>{{ t.fields.length }} 个字段</span>
          <span>·</span>
          <span>{{ t.scope_by_department ? t.department_field || '创建者部门' : '全部门可见' }}</span>
        </div>
        <div class="mt-4 flex items-center gap-2 border-t border-slate-100 pt-3">
          <button class="text-sm text-indigo-600 hover:underline" @click="openEdit(t)">编辑</button>
          <button class="text-sm text-red-500 hover:underline" @click="remove(t)">删除</button>
        </div>
      </div>
    </div>

    <div
      v-if="showEditor"
      class="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-900/40 p-4 backdrop-blur-sm"
      @click.self="closeEditor"
    >
      <div class="my-6 w-full max-w-3xl rounded-2xl bg-white p-6 shadow-2xl">
        <div class="flex items-start justify-between gap-4">
          <div>
            <h2 class="text-lg font-bold text-slate-800">
              {{ isEditing ? '编辑数据表' : '新增数据表' }}
            </h2>
            <p class="mt-0.5 text-xs text-slate-400">定义表信息与字段,保存后立即可在数据看板使用</p>
          </div>
          <button class="text-slate-400 hover:text-slate-600" @click="closeEditor">✕</button>
        </div>

        <div class="mt-5 grid gap-4 sm:grid-cols-2">
          <label class="block">
            <span class="mb-1 block text-sm text-slate-600">表标识 *</span>
            <input
              v-model="form.code"
              :disabled="isEditing"
              placeholder="例如 assets"
              class="w-full rounded-lg border border-slate-200 px-3 py-2 font-mono text-sm disabled:bg-slate-50"
            />
            <span class="mt-1 block text-[11px] text-slate-400">小写字母开头,可含数字/下划线,创建后不可改</span>
          </label>
          <label class="block">
            <span class="mb-1 block text-sm text-slate-600">表名称 *</span>
            <input
              v-model="form.name"
              placeholder="例如 资产台账"
              class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            />
          </label>
          <label class="block sm:col-span-2">
            <span class="mb-1 block text-sm text-slate-600">描述</span>
            <input
              v-model="form.description"
              class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            />
          </label>
          <label class="block">
            <span class="mb-1 block text-sm text-slate-600">标题字段</span>
            <select v-model="form.title_field" class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm">
              <option value="">默认取第一个字段</option>
              <option v-for="f in fieldKeyOptions" :key="f.key" :value="f.key">{{ f.label }}</option>
            </select>
          </label>
          <div class="flex items-end pb-2">
            <label class="flex items-center gap-2 text-sm text-slate-600">
              <input v-model="form.scope_by_department" type="checkbox" class="h-4 w-4 accent-indigo-500" />
              按部门隔离数据
            </label>
          </div>
          <label v-if="form.scope_by_department" class="block sm:col-span-2">
            <span class="mb-1 block text-sm text-slate-600">部门字段</span>
            <select
              v-model="form.department_field"
              class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            >
              <option value="">不指定(记录归属创建者部门)</option>
              <option v-for="f in fieldKeyOptions" :key="f.key" :value="f.key">{{ f.label }}</option>
            </select>
          </label>
        </div>

        <div class="mt-6">
          <div class="flex items-center justify-between">
            <p class="text-sm font-semibold text-slate-700">字段 ({{ form.fields.length }})</p>
            <button class="text-sm text-indigo-600 hover:underline" @click="addField">+ 添加字段</button>
          </div>
          <div class="mt-3 space-y-3">
            <div
              v-for="(f, i) in form.fields"
              :key="i"
              class="rounded-xl border border-slate-100 bg-slate-50/50 p-3"
            >
              <div class="flex flex-wrap items-end gap-2">
                <label class="block w-40">
                  <span class="mb-1 block text-xs text-slate-500">字段标识 *</span>
                  <input
                    v-model="f.key"
                    placeholder="例如 name"
                    class="w-full rounded-lg border border-slate-200 px-2 py-1.5 font-mono text-sm"
                  />
                </label>
                <label class="block w-40">
                  <span class="mb-1 block text-xs text-slate-500">字段名称 *</span>
                  <input
                    v-model="f.label"
                    placeholder="例如 名称"
                    class="w-full rounded-lg border border-slate-200 px-2 py-1.5 text-sm"
                  />
                </label>
                <label class="block w-32">
                  <span class="mb-1 block text-xs text-slate-500">类型</span>
                  <select v-model="f.type" class="w-full rounded-lg border border-slate-200 px-2 py-1.5 text-sm">
                    <option v-for="t in FIELD_TYPES" :key="t.value" :value="t.value">{{ t.label }}</option>
                  </select>
                </label>
                <label class="flex items-center gap-1.5 pb-1.5 text-xs text-slate-600">
                  <input v-model="f.required" type="checkbox" class="h-3.5 w-3.5 accent-indigo-500" />
                  必填
                </label>
                <div class="ml-auto flex items-center gap-1 pb-1">
                  <button class="rounded px-1.5 py-0.5 text-xs text-slate-400 hover:bg-white hover:text-slate-600" @click="moveField(i, -1)">↑</button>
                  <button class="rounded px-1.5 py-0.5 text-xs text-slate-400 hover:bg-white hover:text-slate-600" @click="moveField(i, 1)">↓</button>
                  <button class="rounded px-1.5 py-0.5 text-xs text-red-400 hover:bg-red-50" @click="removeField(i)">删除</button>
                </div>
              </div>
              <label v-if="needsOptions(f.type)" class="mt-2 block">
                <span class="mb-1 block text-xs text-slate-500">可选项(每行一个或逗号分隔)</span>
                <textarea
                  v-model="f.optionsText"
                  rows="2"
                  placeholder="例如:&#10;进行中&#10;已完成"
                  class="w-full rounded-lg border border-slate-200 px-2 py-1.5 text-sm"
                />
              </label>
            </div>
            <p v-if="!form.fields.length" class="rounded-lg border border-dashed border-slate-200 py-6 text-center text-sm text-slate-400">
              至少添加一个字段
            </p>
          </div>
        </div>

        <div class="mt-6 flex items-center gap-3 border-t border-slate-100 pt-4">
          <button
            class="rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-600 disabled:opacity-50"
            :disabled="saving"
            @click="save"
          >
            {{ saving ? '保存中...' : '保存' }}
          </button>
          <button class="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600" @click="closeEditor">
            取消
          </button>
          <span v-if="saveError" class="text-sm text-red-500">{{ saveError }}</span>
        </div>
      </div>
    </div>
  </AppLayout>
</template>
