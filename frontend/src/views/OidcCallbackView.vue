<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()

const error = ref('')
const loading = ref(true)

onMounted(async () => {
  // 后端通过 URL fragment(#token=... / #error=...) 回传结果
  const params = new URLSearchParams(window.location.hash.replace(/^#/, ''))
  const token = params.get('token')
  const next = params.get('next') || '/'
  const err = params.get('error')

  if (err) {
    error.value = err
    loading.value = false
    return
  }
  if (!token) {
    error.value = '缺少登录凭证'
    loading.value = false
    return
  }

  try {
    await auth.acceptToken(token)
    await router.replace(next)
  } catch {
    error.value = '登录信息校验失败,请重试'
    loading.value = false
  }
})
</script>

<template>
  <div class="flex min-h-screen items-center justify-center bg-slate-950 px-6">
    <div
      class="w-full max-w-sm rounded-2xl border border-white/10 bg-white/5 p-8 text-center backdrop-blur-md"
    >
      <template v-if="loading && !error">
        <div
          class="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-white/20 border-t-indigo-400"
        />
        <p class="mt-4 text-sm text-slate-300">正在完成登录...</p>
      </template>

      <template v-else>
        <p class="text-3xl">⚠</p>
        <p class="mt-3 text-sm text-red-300">{{ error }}</p>
        <RouterLink
          to="/login"
          class="mt-6 inline-block rounded-xl bg-gradient-to-r from-indigo-500 to-violet-500 px-5 py-2.5 text-sm font-semibold text-white"
        >
          返回登录
        </RouterLink>
      </template>
    </div>
  </div>
</template>
