import { useCallback, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import {
  login as apiLogin,
  logout as apiLogout,
  refreshToken,
  verifyTwoFactorLogin,
  getMe,
  getMyProperties,
} from '@/services/authApi'
import type { User } from '@/store/authStore'
import { defaultRouteForRole, normaliseRole } from '@/lib/roles'

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

interface LoginResult {
  success: boolean
  requires2FA: boolean
  tempToken?: string | null
}

export function useAuth() {
  const navigate = useNavigate()
  const { accessToken, refreshToken: storedRefreshToken, sessionId, user, isAuthenticated, setAuth, clearAuth } =
    useAuthStore()
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
          window.location.href = '/login'
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

  // On boot, re-fetch the canonical user from /auth/me so a stale role
  // claim in the cached JWT doesn't grant lingering access. If the access
  // token has already expired, defer to the refresh path before calling /me
  // so a single transient 401 doesn't tear down a perfectly valid session.
  useEffect(() => {
    if (!accessToken || !storedRefreshToken) return
    let cancelled = false

    const payload = decodeJwt(accessToken)
    const expiresAt = (payload?.exp ?? 0) * 1000
    const tokenExpired = !expiresAt || expiresAt - Date.now() < 5_000

    const reconcile = async () => {
      try {
        let token = accessToken
        if (tokenExpired) {
          const refreshed = await refreshToken(storedRefreshToken)
          if (cancelled) return
          const refreshedUser = getUserFromToken(refreshed.access_token)
          setAuth({
            accessToken: refreshed.access_token,
            refreshToken: refreshed.refresh_token,
            tokenType: refreshed.token_type,
            sessionId: refreshed.session_id ?? null,
            user: refreshedUser || { id: '', email: '', role: '' },
          })
          token = refreshed.access_token
        }
        const [me, props] = await Promise.all([getMe(), getMyProperties()])
        if (cancelled) return
        const next: User = {
          id: me.id,
          email: me.email,
          role: me.role || getUserFromToken(token)?.role || '',
          name: me.name || undefined,
          properties: props.map((p) => ({
            id: p.property_id,
            name: p.name,
            role_at_property: p.role_at_property,
          })),
        }
        useAuthStore.setState({ user: next })
      } catch {
        // /auth/me failures here are non-fatal — the scheduled refresh
        // (or the next user action) will surface a real auth issue.
      }
    }

    reconcile()
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const finaliseLogin = useCallback(
    async (data: { access_token: string; refresh_token: string; token_type: string; session_id?: string | null }) => {
      const decodedUser = getUserFromToken(data.access_token)
      const userRecord = decodedUser || { id: '', email: '', role: '' }
      let properties: { id: string; name: string; role_at_property: string }[] = []
      try {
        const props = await getMyProperties()
        properties = props.map((p) => ({
          id: p.property_id,
          name: p.name,
          role_at_property: p.role_at_property,
        }))
      } catch {
        // non-fatal — proceed without property roles
      }
      setAuth({
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        tokenType: data.token_type,
        user: { ...decodedUser, properties } || { id: '', email: '', role: '', org_id: '', properties },
      })
      scheduleRefresh(data.access_token, data.refresh_token)
      const target = defaultRouteForRole(normaliseRole(userRecord.role))
      navigate(target)
    },
    [setAuth, scheduleRefresh, navigate],
  )

  const login = useCallback(
    async (email: string, password: string): Promise<LoginResult> => {
      const data = await apiLogin({ email, password })
      if (data.requires_2fa) {
        return { success: false, requires2FA: true, tempToken: data.temp_token ?? null }
      }
      if (!data.access_token || !data.refresh_token) {
        throw new Error('Invalid login response')
      }
      finaliseLogin({
        access_token: data.access_token,
        refresh_token: data.refresh_token,
        token_type: data.token_type,
        session_id: data.session_id,
      })
      return { success: true, requires2FA: false }
    },
    [finaliseLogin],
  )

  const verify2FA = useCallback(
    async (tempToken: string, code: string): Promise<void> => {
      const data = await verifyTwoFactorLogin({ temp_token: tempToken, token: code })
      finaliseLogin(data)
    },
    [finaliseLogin],
  )

  const logout = useCallback(async () => {
    const { refreshToken: rt, sessionId: sid } = useAuthStore.getState()
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
      navigate('/login')
    }
  }, [clearAuth, navigate])

  return {
    user,
    isAuthenticated,
    sessionId,
    login,
    verify2FA,
    logout,
  }
}
