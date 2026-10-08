<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const username = ref('')
const password = ref('')
const showPassword = ref(false)
const submitting = ref(false)
const error = ref('')

const canSubmit = computed(
  () => username.value.trim().length > 0 && password.value.length > 0 && !submitting.value,
)

async function handleSubmit() {
  if (!canSubmit.value) return
  error.value = ''
  submitting.value = true
  try {
    await auth.login(username.value.trim(), password.value)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    await router.replace(redirect)
  } catch (err: unknown) {
    const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    error.value = detail || '登录失败,请检查网络或稍后重试'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="relative flex min-h-screen items-center justify-center overflow-hidden bg-slate-950">
    <!-- 背景装饰 -->
    <div
      class="pointer-events-none absolute -top-40 -left-32 h-[32rem] w-[32rem] rounded-full bg-indigo-600/30 blur-3xl"
    />
    <div
      class="pointer-events-none absolute -bottom-48 -right-24 h-[36rem] w-[36rem] rounded-full bg-cyan-500/20 blur-3xl"
    />
    <div
      class="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_1px_1px,rgba(255,255,255,0.06)_1px,transparent_0)] [background-size:28px_28px]"
    />

    <div
      class="relative z-10 grid w-full max-w-5xl overflow-hidden rounded-3xl border border-white/10 bg-white/5 shadow-2xl backdrop-blur-xl md:grid-cols-2"
    >
      <!-- 左侧品牌区 -->
      <div
        class="hidden flex-col justify-between bg-gradient-to-br from-indigo-600 via-violet-600 to-cyan-500 p-10 text-white md:flex"
      >
        <div class="flex items-center gap-3">
          <div
            class="flex h-11 w-11 items-center justify-center rounded-xl bg-white/15 text-xl font-bold ring-1 ring-white/30"
          >
            II
          </div>
          <span class="text-lg font-semibold tracking-wide">信息集成管理系统</span>
        </div>

        <div class="space-y-4">
          <h1 class="text-3xl font-bold leading-tight">
            统一数据接入<br />高效信息集成
          </h1>
          <p class="max-w-xs text-sm text-white/80">
            整合多源数据,集中管理业务信息,为后续 AD 域账号与细粒度权限管控提供统一入口。
          </p>
        </div>

        <div class="flex items-center gap-2 text-xs text-white/70">
          <span class="h-2 w-2 rounded-full bg-emerald-400" />
          服务运行正常
        </div>
      </div>

      <!-- 右侧登录表单 -->
      <div class="p-8 sm:p-10">
        <div class="mb-8 md:hidden">
          <div class="flex items-center gap-3 text-white">
            <div
              class="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600 font-bold"
            >
              II
            </div>
            <span class="font-semibold">信息集成管理系统</span>
          </div>
        </div>

        <h2 class="text-2xl font-bold text-white">欢迎回来</h2>
        <p class="mt-1 text-sm text-slate-400">请使用您的账号登录系统</p>

        <form class="mt-8 space-y-5" @submit.prevent="handleSubmit">
          <div>
            <label for="username" class="mb-1.5 block text-sm font-medium text-slate-300">
              用户名
            </label>
            <input
              id="username"
              v-model="username"
              type="text"
              autocomplete="username"
              placeholder="请输入用户名"
              class="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-white placeholder-slate-500 outline-none transition focus:border-indigo-400 focus:bg-white/10 focus:ring-2 focus:ring-indigo-500/40"
            />
          </div>

          <div>
            <label for="password" class="mb-1.5 block text-sm font-medium text-slate-300">
              密码
            </label>
            <div class="relative">
              <input
                id="password"
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                autocomplete="current-password"
                placeholder="请输入密码"
                class="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 pr-12 text-white placeholder-slate-500 outline-none transition focus:border-indigo-400 focus:bg-white/10 focus:ring-2 focus:ring-indigo-500/40"
              />
              <button
                type="button"
                class="absolute inset-y-0 right-0 flex items-center px-4 text-xs text-slate-400 transition hover:text-slate-200"
                @click="showPassword = !showPassword"
              >
                {{ showPassword ? '隐藏' : '显示' }}
              </button>
            </div>
          </div>

          <div
            v-if="error"
            class="flex items-start gap-2 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300"
          >
            <span class="mt-0.5">⚠</span>
            <span>{{ error }}</span>
          </div>

          <button
            type="submit"
            :disabled="!canSubmit"
            class="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-indigo-500 to-violet-500 px-4 py-3 font-semibold text-white shadow-lg shadow-indigo-900/40 transition hover:from-indigo-400 hover:to-violet-400 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <span
              v-if="submitting"
              class="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white"
            />
            {{ submitting ? '登录中...' : '登 录' }}
          </button>
        </form>

        <p class="mt-6 text-center text-xs text-slate-500">
          测试账号:<span class="text-slate-400">admin / admin123</span>
        </p>
      </div>
    </div>
  </div>
</template>
