<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

const engineRunning = ref(false)
const marketOpen = ref(false)
const lastFetch = ref('--')
let timer: number | undefined

async function loadStatus() {
  try {
    const resp = await fetch('/monitor-app/api/status', { credentials: 'include' })
    if (!resp.ok) return
    const d = await resp.json()
    engineRunning.value = Boolean(d.engine_running)
    marketOpen.value = Boolean(d.market_open)
    lastFetch.value = d.last_fetch_time || '--'
  } catch {
    /* 忽略 */
  }
}

onMounted(() => {
  loadStatus()
  timer = window.setInterval(loadStatus, 4000)
})
onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
})
</script>

<template>
  <AppLayout>
    <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold text-slate-800">行情监控</h1>
        <p class="mt-1 text-sm text-slate-500">基差 / 跨期价差与证券行情监控</p>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <span
          class="inline-flex items-center gap-1.5 rounded-full bg-white px-3 py-1 text-xs text-slate-600 ring-1 ring-slate-200"
        >
          <span
            class="h-2 w-2 rounded-full"
            :class="engineRunning ? 'bg-emerald-500' : 'bg-slate-300'"
          />
          引擎 {{ engineRunning ? '运行中' : '已停止' }}
        </span>
        <span
          class="inline-flex items-center gap-1.5 rounded-full bg-white px-3 py-1 text-xs text-slate-600 ring-1 ring-slate-200"
        >
          <span class="h-2 w-2 rounded-full" :class="marketOpen ? 'bg-amber-500' : 'bg-slate-300'" />
          盘面 {{ marketOpen ? '开市' : '休市' }}
        </span>
        <span
          class="hidden items-center gap-1.5 rounded-full bg-white px-3 py-1 text-xs text-slate-500 ring-1 ring-slate-200 sm:inline-flex"
        >
          最近抓取 {{ lastFetch }}
        </span>
        <RouterLink
          to="/department"
          class="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-600 transition hover:bg-slate-50"
        >
          ← 返回部门
        </RouterLink>
      </div>
    </div>
    <iframe
      src="/monitor-app/?embed=1"
      title="行情监控"
      class="block h-[calc(100vh-13rem)] min-h-[560px] w-full border-0 bg-transparent"
    />
  </AppLayout>
</template>
