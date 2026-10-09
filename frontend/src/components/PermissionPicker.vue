<script setup lang="ts">
import type { PermissionGroup } from '../api/admin'

const props = defineProps<{
  groups: PermissionGroup[]
  modelValue: Record<string, string>
  disabled?: boolean
  disabledResources?: string[]
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: Record<string, string>): void
}>()

const scopeOptions = [
  { value: 'self', label: '仅本人' },
  { value: 'dept', label: '本部门' },
  { value: 'all', label: '全部' },
]

function isDisabled(resource: string, permDisabled?: boolean): boolean {
  if (props.disabled || permDisabled) return true
  if (props.disabledResources?.includes(resource)) return true
  return false
}

function toggle(code: string, checked: boolean) {
  const next = { ...props.modelValue }
  if (checked) {
    next[code] = next[code] || 'self'
  } else {
    delete next[code]
  }
  emit('update:modelValue', next)
}

function setScope(code: string, scope: string) {
  emit('update:modelValue', { ...props.modelValue, [code]: scope })
}
</script>

<template>
  <div class="space-y-4">
    <div v-for="group in groups" :key="group.resource" class="rounded-xl border border-slate-200 p-4">
      <p class="mb-3 text-sm font-semibold text-slate-700">{{ group.label }}</p>
      <div class="grid gap-2 sm:grid-cols-2">
        <label
          v-for="perm in group.permissions"
          :key="perm.code"
          class="flex items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-slate-50"
          :class="isDisabled(group.resource) ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'"
        >
          <input
            type="checkbox"
            :disabled="isDisabled(group.resource)"
            :checked="perm.code in modelValue"
            class="h-4 w-4 accent-indigo-500"
            @change="toggle(perm.code, ($event.target as HTMLInputElement).checked)"
          />
          <span class="flex-1 text-sm text-slate-600">{{ perm.name }}</span>
          <select
            v-if="perm.code in modelValue"
            :value="modelValue[perm.code]"
            :disabled="isDisabled(group.resource)"
            class="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-600"
            @change="setScope(perm.code, ($event.target as HTMLSelectElement).value)"
          >
            <option v-for="opt in scopeOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
        </label>
      </div>
    </div>
  </div>
</template>
