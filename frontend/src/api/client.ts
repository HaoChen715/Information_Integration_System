import axios, { type AxiosInstance } from 'axios'

const TOKEN_KEY = 'iis_token'
const COOKIE_MAX_AGE = 8 * 60 * 60

function setCookie(name: string, value: string): void {
  document.cookie = `${name}=${encodeURIComponent(value)}; Path=/; SameSite=Lax; Max-Age=${COOKIE_MAX_AGE}`
}

function clearCookie(name: string): void {
  document.cookie = `${name}=; Path=/; SameSite=Lax; Max-Age=0`
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
  // 供内置子应用(/monitor)在浏览器直接跳转时携带身份
  setCookie(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
  clearCookie(TOKEN_KEY)
}

const client: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

client.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      clearToken()
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)

export default client
