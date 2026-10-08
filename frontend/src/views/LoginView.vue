<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
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

// ---- 鼠标视差:直接写 CSS 变量,不触发 Vue 重渲染 ----
const sceneRef = ref<HTMLElement | null>(null)
let rafId = 0
let currentX = 0
let currentY = 0
let targetX = 0
let targetY = 0

function renderParallax() {
  currentX += (targetX - currentX) * 0.08
  currentY += (targetY - currentY) * 0.08
  const el = sceneRef.value
  if (el) {
    el.style.setProperty('--px', currentX.toFixed(4))
    el.style.setProperty('--py', currentY.toFixed(4))
  }
  if (Math.abs(targetX - currentX) < 0.0005 && Math.abs(targetY - currentY) < 0.0005) {
    rafId = 0
    return
  }
  rafId = requestAnimationFrame(renderParallax)
}

function onPointerMove(e: PointerEvent) {
  targetX = e.clientX / window.innerWidth - 0.5
  targetY = e.clientY / window.innerHeight - 0.5
  if (!rafId) rafId = requestAnimationFrame(renderParallax)
}

// ---- 漂浮粒子 ----
interface Particle {
  left: string
  top: string
  size: string
  duration: string
  delay: string
  opacity: number
}

const particles = ref<Particle[]>([])

function buildParticles(count: number): Particle[] {
  const rnd = (min: number, max: number) => min + Math.random() * (max - min)
  return Array.from({ length: count }, () => ({
    left: `${rnd(0, 100).toFixed(2)}%`,
    top: `${rnd(0, 100).toFixed(2)}%`,
    size: `${rnd(2, 5).toFixed(1)}px`,
    duration: `${rnd(12, 26).toFixed(1)}s`,
    delay: `-${rnd(0, 20).toFixed(1)}s`,
    opacity: rnd(0.15, 0.5),
  }))
}

// ---- 性能探测:GPU 不可用 / 低核 / 系统减少动效 → 自动降级 ----
function detectLowPerf(): boolean {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return true
  if ((navigator.hardwareConcurrency || 4) <= 2) return true
  try {
    // 只提供软件渲染时(无 GPU 加速),该调用返回 null
    const canvas = document.createElement('canvas')
    const gl = canvas.getContext('webgl', { failIfMajorPerformanceCaveat: true })
    if (!gl) return true
    gl.getExtension('WEBGL_lose_context')?.loseContext()
  } catch {
    return true
  }
  return false
}

// 可通过 ?effects=on / ?effects=off 强制开关,便于排查
function resolvePerfLite(): boolean {
  const forced = new URLSearchParams(window.location.search).get('effects')
  if (forced === 'off') return true
  if (forced === 'on') return false
  return detectLowPerf()
}

const perfLite = ref(resolvePerfLite())

onMounted(() => {
  if (perfLite.value) return
  particles.value = buildParticles(18)
  window.addEventListener('pointermove', onPointerMove, { passive: true })
})

onBeforeUnmount(() => {
  window.removeEventListener('pointermove', onPointerMove)
  if (rafId) cancelAnimationFrame(rafId)
})

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
  <div
    ref="sceneRef"
    :class="{ 'perf-lite': perfLite }"
    class="login-scene relative flex min-h-screen items-center justify-center overflow-hidden bg-slate-950"
  >
    <!-- 动态光晕(带鼠标视差,transform 走 GPU 合成) -->
    <div class="scene-layer" style="--depth: 44">
      <div class="blob blob-a" />
    </div>
    <div class="scene-layer" style="--depth: 26">
      <div class="blob blob-b" />
    </div>
    <div class="scene-layer" style="--depth: 62">
      <div class="blob blob-c" />
    </div>

    <!-- 漂浮粒子 -->
    <div class="pointer-events-none absolute inset-0 overflow-hidden">
      <span
        v-for="(p, i) in particles"
        :key="i"
        class="particle"
        :style="{
          left: p.left,
          top: p.top,
          width: p.size,
          height: p.size,
          opacity: p.opacity,
          animationDuration: p.duration,
          animationDelay: p.delay,
        }"
      />
    </div>

    <!-- 点阵纹理 -->
    <div
      class="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_1px_1px,rgba(255,255,255,0.06)_1px,transparent_0)] [background-size:28px_28px]"
    />

    <div
      class="login-card relative z-10 grid w-full max-w-5xl overflow-hidden rounded-3xl border border-white/10 shadow-2xl md:grid-cols-2"
    >
      <!-- 左侧品牌区 -->
      <div
        class="hidden flex-col justify-between bg-gradient-to-br from-indigo-600 via-violet-600 to-cyan-500 p-10 text-white md:flex"
      >
        <div class="anim d1 flex items-center gap-3">
          <div
            class="flex h-11 w-11 items-center justify-center rounded-xl bg-white/15 text-xl font-bold ring-1 ring-white/30"
          >
            II
          </div>
          <span class="text-lg font-semibold tracking-wide">信息集成管理系统</span>
        </div>

        <div class="anim d2 space-y-4">
          <h1 class="text-3xl font-bold leading-tight">
            统一数据接入<br />高效信息集成
          </h1>
          <p class="max-w-xs text-sm text-white/80">
            整合多源数据,集中管理业务信息,为后续 AD 域账号与细粒度权限管控提供统一入口。
          </p>
        </div>

        <div class="anim d3 flex items-center gap-2 text-xs text-white/70">
          <span class="relative flex h-2 w-2">
            <span
              class="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"
            />
            <span class="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
          </span>
          服务运行正常
        </div>
      </div>

      <!-- 右侧登录表单 -->
      <div class="p-8 sm:p-10">
        <div class="anim d1 mb-8 md:hidden">
          <div class="flex items-center gap-3 text-white">
            <div
              class="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600 font-bold"
            >
              II
            </div>
            <span class="font-semibold">信息集成管理系统</span>
          </div>
        </div>

        <h2 class="anim d1 text-2xl font-bold text-white">欢迎回来</h2>
        <p class="anim d2 mt-1 text-sm text-slate-400">请使用您的账号登录系统</p>

        <form class="mt-8 space-y-5" @submit.prevent="handleSubmit">
          <div class="anim d2">
            <label for="username" class="mb-1.5 block text-sm font-medium text-slate-300">
              账号
            </label>
            <input
              id="username"
              v-model="username"
              type="text"
              autocomplete="username"
              placeholder="用户名 / 域账号"
              class="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-white placeholder-slate-500 outline-none transition focus:border-indigo-400 focus:bg-white/10 focus:ring-2 focus:ring-indigo-500/40"
            />
          </div>

          <div class="anim d3">
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
            class="anim d3 group relative flex w-full items-center justify-center gap-2 overflow-hidden rounded-xl bg-gradient-to-r from-indigo-500 to-violet-500 px-4 py-3 font-semibold text-white shadow-lg shadow-indigo-900/40 transition hover:from-indigo-400 hover:to-violet-400 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <span class="sheen" aria-hidden="true" />
            <span
              v-if="submitting"
              class="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white"
            />
            {{ submitting ? '登录中...' : '登 录' }}
          </button>
        </form>

        <p class="anim d4 mt-6 text-center text-xs text-slate-500">
          支持 AD 域账号登录(域\账号 或 账号@域)<br />
          测试账号:<span class="text-slate-400">admin / admin123</span>
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ---------- 视差层:transform 由 GPU 合成,只读取 CSS 变量 ---------- */
.scene-layer {
  position: absolute;
  inset: 0;
  pointer-events: none;
  transform: translate3d(
    calc(var(--px, 0) * var(--depth, 0) * 1px),
    calc(var(--py, 0) * var(--depth, 0) * 1px),
    0
  );
}

/* ---------- 光晕:radial-gradient 柔和边缘,无需 GPU blur 滤镜 ---------- */
.blob {
  position: absolute;
  border-radius: 9999px;
  will-change: transform;
}
.blob-a {
  top: -12rem;
  left: -12rem;
  width: 46rem;
  height: 46rem;
  background: radial-gradient(
    circle at center,
    rgba(79, 70, 229, 0.5) 0%,
    rgba(79, 70, 229, 0.18) 38%,
    rgba(79, 70, 229, 0) 70%
  );
  animation: drift-a 22s ease-in-out infinite;
}
.blob-b {
  right: -10rem;
  bottom: -16rem;
  width: 52rem;
  height: 52rem;
  background: radial-gradient(
    circle at center,
    rgba(6, 182, 212, 0.35) 0%,
    rgba(6, 182, 212, 0.12) 40%,
    rgba(6, 182, 212, 0) 72%
  );
  animation: drift-b 28s ease-in-out infinite;
}
.blob-c {
  top: 24%;
  left: 44%;
  width: 34rem;
  height: 34rem;
  background: radial-gradient(
    circle at center,
    rgba(168, 85, 247, 0.32) 0%,
    rgba(168, 85, 247, 0.1) 42%,
    rgba(168, 85, 247, 0) 74%
  );
  animation: drift-c 26s ease-in-out infinite;
}

@keyframes drift-a {
  0%,
  100% {
    transform: translate3d(0, 0, 0) scale(1);
  }
  50% {
    transform: translate3d(5rem, 3rem, 0) scale(1.12);
  }
}
@keyframes drift-b {
  0%,
  100% {
    transform: translate3d(0, 0, 0) scale(1);
  }
  50% {
    transform: translate3d(-4rem, -3rem, 0) scale(1.08);
  }
}
@keyframes drift-c {
  0%,
  100% {
    transform: translate3d(0, 0, 0) scale(1);
  }
  50% {
    transform: translate3d(-3rem, 4rem, 0) scale(1.15);
  }
}

/* ---------- 粒子 ---------- */
.particle {
  position: absolute;
  border-radius: 9999px;
  background: #fff;
  animation-name: float-up;
  animation-timing-function: linear;
  animation-iteration-count: infinite;
  will-change: transform;
}
@keyframes float-up {
  0% {
    transform: translate3d(0, 20px, 0);
  }
  100% {
    transform: translate3d(6px, -140px, 0);
  }
}

/* ---------- 入场动画 ---------- */
.login-card {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  animation: card-in 0.7s cubic-bezier(0.16, 1, 0.3, 1) both;
}
@keyframes card-in {
  from {
    opacity: 0;
    transform: translateY(24px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: none;
  }
}

.anim {
  animation: rise-in 0.55s cubic-bezier(0.22, 1, 0.36, 1) both;
}
.d1 {
  animation-delay: 0.15s;
}
.d2 {
  animation-delay: 0.25s;
}
.d3 {
  animation-delay: 0.35s;
}
.d4 {
  animation-delay: 0.45s;
}
@keyframes rise-in {
  from {
    opacity: 0;
    transform: translateY(14px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}

/* ---------- 按钮扫光 ---------- */
.sheen {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    110deg,
    transparent 30%,
    rgba(255, 255, 255, 0.35) 50%,
    transparent 70%
  );
  transform: translateX(-120%);
}
.group:hover .sheen {
  animation: sheen 1.1s ease;
}
@keyframes sheen {
  to {
    transform: translateX(120%);
  }
}

/* ---------- 低性能 / 无 GPU 环境自动降级 ---------- */
.perf-lite .scene-layer {
  transform: none;
}
.perf-lite .blob,
.perf-lite .particle,
.perf-lite .login-card,
.perf-lite .anim,
.perf-lite .sheen {
  animation: none !important;
}
.perf-lite .particle {
  display: none;
}
.perf-lite .login-card {
  background: rgba(15, 23, 42, 0.92);
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
}

/* ---------- 尊重系统"减少动态效果"设置 ---------- */
@media (prefers-reduced-motion: reduce) {
  .scene-layer {
    transform: none;
  }
  .blob,
  .particle,
  .login-card,
  .anim,
  .sheen {
    animation: none !important;
  }
}
</style>
