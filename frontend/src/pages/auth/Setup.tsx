import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { api } from '@/lib/api'

interface SetupFormData {
  orgName: string
  adminName: string
  adminEmail: string
  adminPassword: string
  confirmPassword: string
}

export default function Setup() {
  const navigate = useNavigate()
  const { setAuth } = useAuthStore()
  const [form, setForm] = useState<SetupFormData>({
    orgName: '',
    adminName: '',
    adminEmail: '',
    adminPassword: '',
    confirmPassword: '',
  })
  const [errors, setErrors] = useState<Partial<Record<keyof SetupFormData, string>>>({})
  const [isLoading, setIsLoading] = useState(false)
  const [globalError, setGlobalError] = useState<string | null>(null)
  const [setupRequired, setSetupRequired] = useState<boolean | null>(null)

  useEffect(() => {
    let cancelled = false
    api
      .get<{ setup_required: boolean }>('/auth/setup-status')
      .then((res) => {
        if (!cancelled) {
          setSetupRequired(res.data.setup_required)
          if (!res.data.setup_required) {
            navigate('/login', { replace: true })
          }
        }
      })
      .catch(() => {
        if (!cancelled) setSetupRequired(false)
      })
    return () => {
      cancelled = true
    }
  }, [navigate])

  const validate = (): boolean => {
    const next: Partial<Record<keyof SetupFormData, string>> = {}
    if (!form.orgName.trim()) next.orgName = 'Organization name is required'
    if (!form.adminName.trim()) next.adminName = 'Admin name is required'
    if (!form.adminEmail.trim()) {
      next.adminEmail = 'Email is required'
    } else if (!/^\S+@\S+\.\S+$/.test(form.adminEmail)) {
      next.adminEmail = 'Invalid email address'
    }
    if (!form.adminPassword) {
      next.adminPassword = 'Password is required'
    } else if (form.adminPassword.length < 10) {
      next.adminPassword = 'Password must be at least 10 characters'
    } else if (!/^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};':"|,.<>/?]).+$/.test(form.adminPassword)) {
      next.adminPassword = 'Password must contain uppercase, lowercase, number, and special character'
    }
    if (form.confirmPassword !== form.adminPassword) {
      next.confirmPassword = 'Passwords do not match'
    }
    setErrors(next)
    return Object.keys(next).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setGlobalError(null)
    if (!validate()) return

    setIsLoading(true)
    try {
      const { data } = await api.post<{
        access_token: string
        refresh_token: string
        token_type: string
        expires_in: number
        session_id: string
      }>('/auth/setup', {
        org_name: form.orgName.trim(),
        admin_name: form.adminName.trim(),
        admin_email: form.adminEmail.trim(),
        admin_password: form.adminPassword,
      })

      const payload = JSON.parse(
        atob(data.access_token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/'))
      )

      setAuth({
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        tokenType: data.token_type,
        user: {
          id: payload.sub || '',
          email: payload.email || '',
          role: payload.role || 'Admin',
          name: payload.name || '',
          org_id: payload.org_id || '',
        },
      })

      navigate('/dashboard', { replace: true })
    } catch (err: unknown) {
      console.error('Setup error:', err)
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response?: { data?: { detail?: string }; status?: number }; message?: string }
        if (axiosErr.response?.status === 403) {
          setGlobalError('Setup has already been completed. Please log in.')
        } else if (axiosErr.response?.status === 500) {
          setGlobalError(
            axiosErr.response?.data?.detail ||
              'Server error during setup. Please check Docker logs for details.',
          )
        } else if (!axiosErr.response) {
          setGlobalError('Network error — cannot reach the backend. Is Docker running?')
        } else {
          setGlobalError(axiosErr.response?.data?.detail || 'Setup failed. Please try again.')
        }
      } else if (err instanceof Error) {
        setGlobalError(err.message || 'An unexpected error occurred.')
      } else {
        setGlobalError('An unexpected error occurred.')
      }
    } finally {
      setIsLoading(false)
    }
  }

  if (setupRequired === null) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-pulse h-8 w-8 rounded-full bg-brand-600" />
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 to-gray-100 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shadow-sm mx-auto mb-3">
            <span className="text-white font-bold text-lg">B</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Welcome to Brekora</h1>
          <p className="text-sm text-gray-500 mt-1">Complete the one-time setup to get started</p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6 space-y-4"
        >
          {globalError && (
            <div className="p-3 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm" role="alert">
              {globalError}
            </div>
          )}

          <div>
            <label htmlFor="orgName" className="block text-sm font-medium text-gray-700 mb-1">
              Organization Name
            </label>
            <input
              id="orgName"
              type="text"
              value={form.orgName}
              onChange={(e) => setForm((f) => ({ ...f, orgName: e.target.value }))}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
              placeholder="e.g., Sunset Hospitality"
            />
            {errors.orgName && <p className="mt-1 text-xs text-red-600">{errors.orgName}</p>}
          </div>

          <div>
            <label htmlFor="adminName" className="block text-sm font-medium text-gray-700 mb-1">
              Admin Full Name
            </label>
            <input
              id="adminName"
              type="text"
              value={form.adminName}
              onChange={(e) => setForm((f) => ({ ...f, adminName: e.target.value }))}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
              placeholder="e.g., Rahul Sharma"
            />
            {errors.adminName && <p className="mt-1 text-xs text-red-600">{errors.adminName}</p>}
          </div>

          <div>
            <label htmlFor="adminEmail" className="block text-sm font-medium text-gray-700 mb-1">
              Admin Email
            </label>
            <input
              id="adminEmail"
              type="email"
              value={form.adminEmail}
              onChange={(e) => setForm((f) => ({ ...f, adminEmail: e.target.value }))}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
              placeholder="admin@example.com"
            />
            {errors.adminEmail && <p className="mt-1 text-xs text-red-600">{errors.adminEmail}</p>}
          </div>

          <div>
            <label htmlFor="adminPassword" className="block text-sm font-medium text-gray-700 mb-1">
              Password
            </label>
            <input
              id="adminPassword"
              type="password"
              value={form.adminPassword}
              onChange={(e) => setForm((f) => ({ ...f, adminPassword: e.target.value }))}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
              placeholder="Min. 10 characters"
            />
            {errors.adminPassword && (
              <p className="mt-1 text-xs text-red-600">{errors.adminPassword}</p>
            )}
          </div>

          <div>
            <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 mb-1">
              Confirm Password
            </label>
            <input
              id="confirmPassword"
              type="password"
              value={form.confirmPassword}
              onChange={(e) => setForm((f) => ({ ...f, confirmPassword: e.target.value }))}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
              placeholder="Repeat password"
            />
            {errors.confirmPassword && (
              <p className="mt-1 text-xs text-red-600">{errors.confirmPassword}</p>
            )}
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-2.5 bg-brand-600 text-white text-sm font-semibold rounded-lg hover:bg-brand-700 disabled:opacity-60 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
          >
            {isLoading ? 'Setting up...' : 'Complete Setup'}
          </button>
        </form>

        <p className="text-center text-xs text-gray-400 mt-4">
          This is a one-time setup. Once complete, this page will no longer be accessible.
        </p>
      </div>
    </div>
  )
}
