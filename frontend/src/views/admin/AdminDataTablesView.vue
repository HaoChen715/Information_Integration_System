<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import AppLayout from '../../components/AppLayout.vue'
import * as dtApi from '../../api/datatables'
import * as adminApi from '../../api/admin'
import { parseCreateTableDdl } from '../../utils/ddl'
import type { Department } from '../../api/admin'
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

interface FieldDraftOption {
  value: string
  color: string
}

interface FieldDraft {
  key: string
  label: string
  type: string
  required: boolean
  options: FieldDraftOption[]
}

const tables = ref<DataTable[]>([])
const departments = ref<Department[]>([])
const loading = ref(false)
const error = ref('')

const showEditor = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const saveError = ref('')
const ddlText = ref('')
const ddlError = ref('')
const ddlNotice = ref('')

const form = ref({
  code: '',
  name: '',
  description: '',
  title_field: '',
  scope_by_department: true,
  visible_departments: [] as string[],
  heartbeat_field: '',
  heartbeat_values: [] as string[],
  fields: [] as FieldDraft[],
})

const isEditing = computed(() => editingId.value !== null)
const fieldKeyOptions = computed(() =>
  form.value.fields.filter((f) => f.key.trim()).map((f) => ({ key: f.key.trim(), label: f.label || f.key })),
)
const heartbeatFieldOptions = computed(() =>
  form.value.fields
    .filter((f) => f.key.trim() && f.type === 'single_select')
    .map((f) => ({ key: f.key.trim(), label: f.label || f.key })),
)
const heartbeatDraft = computed(() =>
  form.value.fields.find((f) => f.key.trim() === form.value.heartbeat_field),
)
const heartbeatOptionValues = computed(() =>
  heartbeatDraft.value
    ? heartbeatDraft.value.options.map((o) => o.value).filter((v) => v.trim())
    : [],
)

function onHeartbeatFieldChange() {
  form.value.heartbeat_values = form.value.heartbeat_values.filter((v) =>
    heartbeatOptionValues.value.includes(v),
  )
}

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

function addOption(field: FieldDraft) {
  field.options.push({ value: '', color: OPTION_COLORS[field.options.length % OPTION_COLORS.length] })
}

function removeOption(field: FieldDraft, index: number) {
  field.options.splice(index, 1)
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [tableRows, deptOptions] = await Promise.all([
      dtApi.listAdminTables(),
      adminApi.fetchDepartmentOptions().catch(() => [] as Department[]),
    ])
    tables.value = tableRows
    departments.value = deptOptions
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
  ddlText.value = ''
  ddlError.value = ''
  ddlNotice.value = ''
  form.value = {
    code: '',
    name: '',
    description: '',
    title_field: '',
    scope_by_department: true,
    visible_departments: [],
    heartbeat_field: '',
    heartbeat_values: [],
    fields: [],
  }
  addField()
  showEditor.value = true
}

function openEdit(table: DataTable) {
  editingId.value = table.id
  saveError.value = ''
  ddlError.value = ''
  ddlNotice.value = ''
  form.value = {
    code: table.code,
    name: table.name,
    description: table.description ?? '',
    title_field: table.title_field ?? '',
    scope_by_department: table.scope_by_department,
    visible_departments: [...(table.visible_departments ?? [])],
    heartbeat_field: table.heartbeat_field ?? '',
    heartbeat_values: [...(table.heartbeat_values ?? [])],
    fields: table.fields.map((f) => ({
      key: f.key,
      label: f.label,
      type: f.type,
      required: f.required,
      options: (f.options ?? []).map((o) => ({ value: o.value, color: o.color || '#e0e7ff' })),
    })),
  }
  showEditor.value = true
}

function closeEditor() {
  showEditor.value = false
  saving.value = false
}

function addField() {
  form.value.fields.push({ key: '', label: '', type: 'text', required: false, options: [] })
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

function applyDdl() {
  ddlError.value = ''
  ddlNotice.value = ''
  try {
    const parsed = parseCreateTableDdl(ddlText.value)
    form.value.code = parsed.code
    form.value.name = parsed.name
    form.value.fields = parsed.fields.map((field) => ({
      key: field.key,
      label: field.label,
      type: field.type,
      required: field.required,
      options: parseOptions(field.optionsText).map((option) => ({
        value: option.value,
        color: option.color || OPTION_COLORS[0],
      })),
    }))
    form.value.title_field = parsed.fields[0]?.key || ''
    ddlNotice.value = `已解析 ${parsed.fields.length} 个字段,请确认表标识、可见部门后保存。`
  } catch (err: unknown) {
    ddlError.value = (err as Error)?.message || 'DDL 解析失败'
  }
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
  if (form.value.scope_by_department && !form.value.visible_departments.length) {
    saveError.value = '按部门隔离时,请至少选择一个可见部门'
    return null
  }
  if (form.value.heartbeat_field && !form.value.heartbeat_values.length) {
    saveError.value = '请勾选心跳字段中需要闪烁的状态值'
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
    const options: FieldOption[] = []
    if (needsOptions(f.type)) {
      const seenValues = new Set<string>()
      for (const option of f.options) {
        const value = option.value.trim()
        if (!value || seenValues.has(value)) continue
        seenValues.add(value)
        options.push({ value, color: option.color || OPTION_COLORS[0] })
      }
      if (!options.length) {
        saveError.value = `字段「${label}」至少需要一个选项`
        return null
      }
    }
    fields.push({
      key,
      label,
      type: f.type,
      required: f.required,
      options,
    })
  }
  return {
    code: form.value.code.trim(),
    name: form.value.name.trim(),
    description: form.value.description.trim() || null,
    title_field: form.value.title_field,
    scope_by_department: form.value.scope_by_department,
    visible_departments: form.value.scope_by_department ? form.value.visible_departments : [],
    heartbeat_field: form.value.heartbeat_field,
    heartbeat_values: form.value.heartbeat_field ? form.value.heartbeat_values : [],
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
          <span>{{ t.scope_by_department ? (t.visible_departments?.join('、') || '未设置部门') : '全部门可见' }}</span>
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

        <div v-if="!isEditing" class="mt-5 rounded-xl border border-indigo-100 bg-indigo-50/50 p-4">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <div>
              <p class="text-sm font-semibold text-indigo-700">从 DDL 快速创建</p>
              <p class="mt-0.5 text-[11px] text-indigo-500">
                粘贴 CREATE TABLE 语句,自动解析表名与字段(不执行 SQL,仅生成表定义)
              </p>
            </div>
            <button
              class="rounded-lg bg-indigo-500 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-600"
              @click="applyDdl"
            >
              解析并填充
            </button>
          </div>
          <textarea
            v-model="ddlText"
            rows="4"
            placeholder="CREATE TABLE assets (&#10;  name VARCHAR(128) NOT NULL,&#10;  status VARCHAR(32) CHECK (status IN ('在用','闲置')),&#10;  amount NUMERIC(12,2)&#10;);"
            class="mt-3 w-full rounded-lg border border-indigo-100 bg-white px-3 py-2 font-mono text-xs outline-none focus:border-indigo-300"
          />
          <p v-if="ddlError" class="mt-1 text-xs text-red-500">{{ ddlError }}</p>
          <p v-if="ddlNotice" class="mt-1 text-xs text-emerald-600">{{ ddlNotice }}</p>
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
          <div v-if="form.scope_by_department" class="block sm:col-span-2">
            <span class="mb-1 block text-sm text-slate-600">归属 / 可见部门 *</span>
            <div class="flex flex-wrap gap-2">
              <label
                v-for="d in departments"
                :key="d.id"
                class="flex cursor-pointer items-center gap-1.5 rounded-full border border-slate-200 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
              >
                <input
                  v-model="form.visible_departments"
                  type="checkbox"
                  :value="d.name"
                  class="h-3.5 w-3.5 accent-indigo-500"
                />
                {{ d.name }}
              </label>
              <span v-if="!departments.length" class="text-sm text-slate-400">
                暂无部门,请先在「部门管理」创建
              </span>
            </div>
            <span class="mt-1 block text-[11px] text-slate-400">
              记录按这里选择的部门归属;用户只能看到自己部门在其中的数据表
            </span>
          </div>
          <div class="block sm:col-span-2">
            <span class="mb-1 block text-sm text-slate-600">心跳字段(单选,可选)</span>
            <select
              v-model="form.heartbeat_field"
              class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              @change="onHeartbeatFieldChange"
            >
              <option value="">不启用</option>
              <option v-for="f in heartbeatFieldOptions" :key="f.key" :value="f.key">{{ f.label }}</option>
            </select>
            <div v-if="form.heartbeat_field" class="mt-2 rounded-lg bg-slate-50 px-3 py-2">
              <p class="text-xs text-slate-500">勾选需要闪烁的状态值:</p>
              <div class="mt-1.5 flex flex-wrap gap-2">
                <label
                  v-for="v in heartbeatOptionValues"
                  :key="v"
                  class="flex cursor-pointer items-center gap-1.5 rounded-full border border-slate-200 bg-white px-2.5 py-1 text-xs text-slate-600"
                >
                  <input v-model="form.heartbeat_values" type="checkbox" :value="v" class="h-3.5 w-3.5 accent-indigo-500" />
                  {{ v }}
                </label>
                <span v-if="!heartbeatOptionValues.length" class="text-xs text-amber-600">
                  该字段暂无可选项,请先在字段设置里填写选项
                </span>
              </div>
              <p class="mt-1 text-[11px] text-slate-400">闪烁颜色取自该字段选项颜色</p>
            </div>
          </div>
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
              <div v-if="needsOptions(f.type)" class="mt-2 rounded-lg border border-slate-200 bg-white p-2.5">
                <div class="mb-1.5 flex items-center justify-between">
                  <span class="text-xs text-slate-500">可选项与颜色</span>
                  <button class="text-xs text-indigo-600 hover:underline" @click="addOption(f)">+ 添加选项</button>
                </div>
                <div class="space-y-1.5">
                  <div v-for="(opt, oi) in f.options" :key="oi" class="flex flex-wrap items-center gap-2">
                    <input
                      v-model="opt.value"
                      placeholder="选项值"
                      class="min-w-0 flex-1 rounded-lg border border-slate-200 px-2 py-1 text-sm"
                    />
                    <input
                      v-model="opt.color"
                      type="color"
                      class="h-8 w-10 cursor-pointer rounded border border-slate-200 bg-white p-0.5"
                    />
                    <div class="flex items-center gap-1">
                      <button
                        v-for="c in OPTION_COLORS"
                        :key="c"
                        type="button"
                        class="h-5 w-5 rounded-full border border-white ring-1 ring-slate-200 transition hover:scale-110"
                        :style="{ background: c }"
                        :title="c"
                        @click="opt.color = c"
                      />
                    </div>
                    <button class="text-xs text-red-400 hover:text-red-600" @click="removeOption(f, oi)">删除</button>
                  </div>
                  <p v-if="!f.options.length" class="text-xs text-slate-400">还没有选项,点击「添加选项」</p>
                </div>
              </div>
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
