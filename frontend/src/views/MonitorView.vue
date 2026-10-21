<script setup lang="ts"></script>

<template>
  <AppLayout wide>
    <div class="mb-3 flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-slate-800">行情监控</h1>
        <p class="mt-1 text-sm text-slate-500">基差 / 跨期价差与证券行情监控(已融入本系统)</p>
      </div>
      <RouterLink
        to="/department"
        class="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-600 transition hover:bg-slate-50"
      >
        ← 返回部门
      </RouterLink>
    </div>
    <iframe
      src="/monitor-app/?embed=1"
      title="行情监控"
      class="block h-[calc(100vh-10.5rem)] w-full border-0 bg-transparent"
    />
  </AppLayout>
</template>
