<script setup lang="ts">
import { onMounted, ref } from 'vue'

import AppLayout from '../../components/AppLayout.vue'
import * as baserowApi from '../../api/baserow'
import type { BaserowSource } from '../../api/baserow'

const sources = ref<BaserowSource[]>([])
const options = ref<baserowApi.BaserowOptions | null>(null)
const showForm = ref(false)
const saving = ref(false)
const message = ref('')
const testMsg = ref('')
const testing = ref(false)

const form = ref({
  id: null as number | null,
  name: '',
  url: '',
  token: '',
  department_field: '',
  departments: [] as string[],
  enabled: true,
  tables: [] as { name: string; table_id: string; title_field: string; enabled: boolean }[],
})

async function load() {
  sources.value = await baserowApi.fetchSources()
  try {
    options.value = await baserowApi.fetchOptions()
  } catch {
    options.value = null
  }
}

function startCreate() {
  message.value = ''
  testMsg.value = ''
  form.value = {
    id: null,
    name: '',
    url: options.value?.default_url || '',
    token: '',
    department_field: '',
    departments: [],
    enabled: true,
    tables: [{ name: '', table_id: '', title_field: '', enabled: true }],
  }
  showForm.value = true
}

function startEdit(src: BaserowSource) {
  message.value = ''
  testMsg.value = ''
  form.value = {
    id: src.id,
    name: src.name,
    url: src.url,
    token: '',
    department_field: src.department_field,
    departments: [...src.departments],
    enabled: src.enabled,
    tables: src.tables.map((t) => ({ name: t.name, table_id: t.table_id, title_field: t.title_field, enabled: t.enabled })),
  }
  showForm.value = true
}

function toggleDepartment(name: string) {
  const i = form.value.departments.indexOf(name)
  if (i >= 0) form.value.departments.splice(i, 1)
  else form.value.departments.push(name)
}

function addTable() {
  form.value.tables.push({ name: '', table_id: '', title_field: '', enabled: true })
}
function removeTable(i: number) {
  form.value.tables.splice(i, 1)
}

async function testRow(i: number) {
  testMsg.value = ''
  const t = form.value.tables[i]
  if (!t.table_id) {
    testMsg.value = '请先填写表 ID'
    return
  }
  if (!form.value.token) {
    testMsg.value = '测试需要填写令牌(编辑时请重新输入令牌)'
    return
  }
  testing.value = true
  try {
    const res = await baserowApi.testConnection({
      url: form.value.url,
      token: form.value.token,
      table_id: t.table_id,
    })
    testMsg.value = `✅ 连接成功:${res.count} 条数据,字段:${res.fields.join('、')}`
  } catch (err: unknown) {
    testMsg.value =
      '❌ ' + ((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '测试失败')
  } finally {
    testing.value = false
  }
}

async function save() {
  saving.value = true
  message.value = ''
  const payload = {
    name: form.value.name,
    url: form.value.url,
    department_field: form.value.department_field,
    departments: form.value.departments,
    enabled: form.value.enabled,
    tables: form.value.tables.filter((t) => t.name && t.table_id),
    ...(form.value.token ? { token: form.value.token } : {}),
  }
  try {
    if (form.value.id === null) {
      await baserowApi.createSource(payload)
    } else {
      await baserowApi.updateSource(form.value.id, payload)
    }
    showForm.value = false
    await load()
  } catch (err: unknown) {
    message.value =
      (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '保存失败'
  } finally {
    saving.value = false
  }
}

async function remove(src: BaserowSource) {
  if (!confirm(`确认删除数据源「${src.name}」?`)) return
  try {
    await baserowApi.deleteSource(src.id)
    await load()
  } catch (err: unknown) {
    alert((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '删除失败')
  }
}

onMounted(load)
</script>

<template>
  <AppLayout>
    <div class="flex items-start justify-between">
      <div>
        <h1 class="text-2xl font-bold text-slate-800">数据源配置</h1>
        <p class="mt-1 text-sm text-slate-500">
          为每个 Baserow 工作区配置令牌与数据表;数据看板将使用此处配置的数据源。
        </p>
      </div>
      <button
        class="rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-600"
        @click="startCreate"
      >
        新建数据源
      </button>
    </div>

    <div class="mt-6 grid gap-4 md:grid-cols-2">
      <div v-for="src in sources" :key="src.id" class="rounded-2xl border border-slate-200 bg-white p-5">
        <div class="flex items-center justify-between">
          <p class="font-semibold text-slate-800">
            {{ src.name }}
            <span
              v-if="!src.enabled"
              class="ml-1 rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-400"
              >停用</span
            >
          </p>
          <div class="text-sm">
            <button class="mr-3 text-indigo-600 hover:underline" @click="startEdit(src)">编辑</button>
            <button class="text-red-500 hover:underline" @click="remove(src)">删除</button>
          </div>
        </div>
        <p class="mt-1 text-xs text-slate-400">
          {{ src.url }} · 令牌 {{ src.token_hint || '未设置' }} · 可见部门
          {{ src.departments.length ? src.departments.join('、') : '全部' }}
        </p>
        <ul class="mt-3 space-y-1">
          <li
            v-for="t in src.tables"
            :key="t.id"
            class="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-1.5 text-sm"
          >
            <span class="text-slate-700">{{ t.name }}</span>
            <span class="text-xs text-slate-400">表 {{ t.table_id }}</span>
          </li>
          <li v-if="!src.tables.length" class="text-xs text-slate-400">未配置数据表</li>
        </ul>
      </div>
      <div
        v-if="!sources.length"
        class="rounded-2xl border border-dashed border-slate-200 bg-white px-6 py-16 text-center text-slate-400 md:col-span-2"
      >
        还没有数据源,点击右上角"新建数据源"开始配置
      </div>
    </div>

    <!-- 编辑弹层 -->
    <div v-if="showForm" class="fixed inset-0 z-50 flex justify-end bg-slate-900/40" @click.self="showForm = false">
      <div class="h-full w-full max-w-2xl overflow-y-auto bg-white p-6 shadow-xl">
        <div class="flex items-center justify-between">
          <h2 class="text-lg font-bold text-slate-800">
            {{ form.id === null ? '新建数据源' : '编辑数据源' }}
          </h2>
          <button class="text-slate-400 hover:text-slate-600" @click="showForm = false">✕</button>
        </div>

        <div class="mt-5 space-y-4">
          <div class="grid grid-cols-2 gap-3">
            <label class="block">
              <span class="mb-1 block text-sm text-slate-600">名称(工作区)</span>
              <input v-model="form.name" class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm" />
            </label>
            <label class="block">
              <span class="mb-1 block text-sm text-slate-600">Baserow 地址</span>
              <input v-model="form.url" placeholder="https://baserow.example.com" class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm" />
            </label>
          </div>

          <label class="block">
            <span class="mb-1 block text-sm text-slate-600">
              数据库令牌
              <span v-if="form.id !== null" class="text-xs text-slate-400">(留空表示不修改)</span>
            </span>
            <input
              v-model="form.token"
              type="password"
              placeholder="在该工作区「数据库令牌」处创建"
              class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            />
          </label>

          <div>
            <span class="mb-1 block text-sm text-slate-600">可见部门(不选=所有部门均可见)</span>
            <div class="flex flex-wrap gap-2">
              <template v-if="options?.departments?.length">
                <button
                  v-for="d in options.departments"
                  :key="d"
                  type="button"
                  class="rounded-full px-3 py-1 text-sm font-medium ring-1 transition"
                  :class="
                    form.departments.includes(d)
                      ? 'bg-indigo-500 text-white ring-indigo-500'
                      : 'bg-white text-slate-600 ring-slate-200 hover:bg-slate-50'
                  "
                  @click="toggleDepartment(d)"
                >
                  {{ d }}
                </button>
              </template>
              <span v-else class="text-xs text-slate-400">请先在「部门管理」里添加部门</span>
            </div>
          </div>

          <label class="flex items-center gap-2 text-sm text-slate-600">
            <input v-model="form.enabled" type="checkbox" class="h-4 w-4 accent-indigo-500" />启用
          </label>

          <div>
            <div class="mb-2 flex items-center justify-between">
              <p class="text-sm font-semibold text-slate-700">数据表</p>
              <button class="text-sm text-indigo-600 hover:underline" @click="addTable">+ 添加表</button>
            </div>
            <div class="space-y-2">
              <div
                v-for="(t, i) in form.tables"
                :key="i"
                class="flex items-center gap-2 rounded-lg border border-slate-200 p-2"
              >
                <input
                  v-model="t.name"
                  placeholder="表名"
                  class="w-40 rounded-md border border-slate-200 px-2 py-1.5 text-sm"
                />
                <input
                  v-model="t.table_id"
                  placeholder="表 ID"
                  class="w-24 rounded-md border border-slate-200 px-2 py-1.5 text-sm"
                />
                <input
                  v-model="t.title_field"
                  placeholder="标题字段(默认首列)"
                  class="w-40 rounded-md border border-slate-200 px-2 py-1.5 text-sm"
                />
                <label class="flex items-center gap-1 text-xs text-slate-500">
                  <input v-model="t.enabled" type="checkbox" class="h-3.5 w-3.5 accent-indigo-500" />启用
                </label>
                <button class="text-xs text-slate-500 hover:underline" @click="testRow(i)">测试</button>
                <button class="text-xs text-red-500 hover:underline" @click="removeTable(i)">删除</button>
              </div>
            </div>
            <p class="mt-1 text-xs text-slate-400">
              表 ID 从 Baserow 打开该表的网址中取:`/table/&lt;表ID&gt;/`
            </p>
            <p v-if="testMsg" class="mt-2 text-sm" :class="testMsg.startsWith('✅') ? 'text-emerald-600' : 'text-red-500'">
              {{ testMsg }}
            </p>
          </div>

          <div class="flex items-center gap-3 pt-2">
            <button
              class="rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-600 disabled:opacity-50"
              :disabled="saving"
              @click="save"
            >
              {{ saving ? '保存中...' : '保存' }}
            </button>
            <button class="rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-600" @click="showForm = false">
              取消
            </button>
            <span v-if="message" class="text-sm text-red-500">{{ message }}</span>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>
