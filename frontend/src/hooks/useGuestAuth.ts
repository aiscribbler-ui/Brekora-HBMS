import { useCallback, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useGuestAuthStore } from '@/store/guestAuthStore'
import { login as apiLogin, logout as apiLogout, refreshToken } from '@/services/authApi'
import type { User } from '@/store/authStore'

function decodeJwt(token: string): { exp?: number; sub?: string; email?: string; role?: string; name?: string; org_id?: string } | null {
  try {
    const base64Url = token.split('.')[1]
    if (!base64Url) return null
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join(''),
    )
    return JSON.parse(jsonPayload)
  } catch {
    return null
  }
}

function getUserFromToken(token: string): User | null {
  const payload = decodeJwt(token)
  if (!payload) return null
  return {
    id: payload.sub || '',
    email: payload.email || '',
    role: payload.role || '',
    name: payload.name || '',
    org_id: payload.org_id || '',
  }
}

export function useGuestAuth() {
  const navigate = useNavigate()
  const { accessToken, refreshToken: storedRefreshToken, user, isAuthenticated, setAuth, clearAuth } =
    useGuestAuthStore()
  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const scheduleRefresh = useCallback(
    (token: string, refresh: string) => {
      const payload = decodeJwt(token)
      if (!payload?.exp) return
      const expiresAt = payload.exp * 1000
      const now = Date.now()
      const refreshIn = Math.max(expiresAt - now - 60 * 1000, 1000)

      if (refreshTimerRef.current) {
        clearTimeout(refreshTimerRef.current)
      }
      refreshTimerRef.current = setTimeout(async () => {
        try {
          const data = await refreshToken(refresh)
          const newUser = getUserFromToken(data.access_token)
          setAuth({
            accessToken: data.access_token,
            refreshToken: data.refresh_token,
            tokenType: data.token_type,
            user: newUser || { id: '', email: '', role: '', org_id: '' },
          })
          scheduleRefresh(data.access_token, data.refresh_token)
        } catch {
          clearAuth()
          window.location.href = '/guest/login'
        }
      }, refreshIn)
    },
    [setAuth, clearAuth],
  )

  useEffect(() => {
    if (accessToken && storedRefreshToken) {
      scheduleRefresh(accessToken, storedRefreshToken)
    }
    return () => {
      if (refreshTimerRef.current) {
        clearTimeout(refreshTimerRef.current)
      }
    }
  }, [accessToken, storedRefreshToken, scheduleRefresh])

  const login = useCallback(
    async (email: string, password: string): Promise<boolean> => {
      const data = await apiLogin({ email, password })
      if (data.requires_2fa) {
        throw new Error('2FA is not supported on the guest portal')
      }
      if (!data.access_token || !data.refresh_token) {
        throw new Error('Invalid login response')
      }
      const decodedUser = getUserFromToken(data.access_token)
      setAuth({
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        tokenType: data.token_type,
        user: decodedUser || { id: '', email: '', role: '', org_id: '' },
      })
      scheduleRefresh(data.access_token, data.refresh_token)
      navigate('/guest')
      return true
    },
    [setAuth, scheduleRefresh, navigate],
  )

  const logout = useCallback(async () => {
    const { refreshToken: rt, sessionId: sid } = useGuestAuthStore.getState()
    try {
      if (rt) {
        await apiLogout(rt, sid)
      }
    } catch {
      // ignore errors during logout
    } finally {
      if (refreshTimerRef.current) {
        clearTimeout(refreshTimerRef.current)
      }
      clearAuth()
      navigate('/guest/login')
    }
  }, [clearAuth, navigate])

  return {
    user,
    isAuthenticated,
    login,
    logout,
  }
}
