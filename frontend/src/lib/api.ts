import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'
import { useAuthStore } from '@/store/authStore'
import { useGuestAuthStore } from '@/store/guestAuthStore'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
})

function pickActiveToken(): { token: string; isGuest: boolean } | null {
  const manager = useAuthStore.getState()
  if (manager.accessToken) {
    return { token: manager.accessToken, isGuest: false }
  }
  const guest = useGuestAuthStore.getState()
  if (guest.accessToken) {
    return { token: guest.accessToken, isGuest: true }
  }
  return null
}

api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const { accessToken, user } = useAuthStore.getState()
    if (accessToken) {
      config.headers.set('Authorization', `Bearer ${accessToken}`)
    }
    if (user?.org_id) {
      config.headers.set('X-Org-ID', user.org_id)
    }
    return config
  },
  (error) => Promise.reject(error),
)

// Paths that handle 401s themselves; the interceptor must NOT wipe auth or
// redirect when these fail, otherwise login/refresh/me failures cause infinite
// bounce loops or kick the user out on cold-load races.
const AUTH_BYPASS_PREFIXES = [
  '/auth/login',
  '/auth/refresh',
  '/auth/logout',
  '/auth/me',
  '/auth/2fa/login-verify',
  '/auth/google',
  '/guest/signup',
]

function shouldBypassAuthRedirect(url: string | undefined): boolean {
  if (!url) return false
  return AUTH_BYPASS_PREFIXES.some((prefix) => url.includes(prefix))
}

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401 && !shouldBypassAuthRedirect(error.config?.url)) {
      const guest = useGuestAuthStore.getState()
      const manager = useAuthStore.getState()
      if (guest.isAuthenticated && !manager.isAuthenticated) {
        guest.clearAuth()
        window.location.href = '/guest/login'
      } else if (manager.isAuthenticated) {
        manager.clearAuth()
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)

export function isAxiosError<T = { detail?: string }>(error: unknown): error is AxiosError<T> {
  return axios.isAxiosError(error)
}
