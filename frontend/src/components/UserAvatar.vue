<script setup lang="ts">
import { computed, ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    name?: string | null
    username?: string
    src?: string | null
    size?: number
  }>(),
  { name: '', username: '', src: null, size: 40 },
)

const palette = [
  'bg-indigo-500',
  'bg-violet-500',
  'bg-sky-500',
  'bg-emerald-500',
  'bg-rose-500',
  'bg-amber-500',
  'bg-cyan-500',
  'bg-fuchsia-500',
]

function hash(str: string): number {
  let h = 0
  for (let i = 0; i < str.length; i++) {
    h = (h * 31 + str.charCodeAt(i)) | 0
  }
  return Math.abs(h)
}

const source = computed(() => props.name || props.username || '?')
const initials = computed(() => {
  const value = source.value.trim()
  if (!value) return '?'
  const isCjk = /[\u4e00-\u9fa5]/.test(value)
  if (isCjk) return value.slice(-2)
  const parts = value.split(/[\s._-]+/).filter(Boolean)
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
  return value.slice(0, 2).toUpperCase()
})
const colorClass = computed(() => palette[hash(source.value) % palette.length])

const failed = ref(false)
watch(
  () => props.src,
  () => {
    failed.value = false
  },
)

const showImage = computed(() => Boolean(props.src) && !failed.value)
</script>

<template>
  <img
    v-if="showImage"
    :src="src || ''"
    alt=""
    class="inline-block rounded-full object-cover"
    :style="{ width: `${size}px`, height: `${size}px` }"
    @error="failed = true"
  />
  <span
    v-else
    class="inline-flex select-none items-center justify-center rounded-full font-semibold text-white"
    :class="colorClass"
    :style="{
      width: `${size}px`,
      height: `${size}px`,
      fontSize: `${Math.round(size * 0.38)}px`,
    }"
  >
    {{ initials }}
  </span>
</template>
