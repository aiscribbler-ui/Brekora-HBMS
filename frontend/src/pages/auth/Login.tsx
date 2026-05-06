import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { loginSchema, type LoginInput } from '@/lib/validation'
import { isAxiosError } from '@/lib/api'
import LiveRegion from '@/components/a11y/LiveRegion'
import GoogleSignInButton from '@/components/auth/GoogleSignInButton'
import { googleLogin } from '@/services/authApi'
import { useAuthStore } from '@/store/authStore'
import { defaultRouteForRole, normaliseRole } from '@/lib/roles'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginInput>({
    resolver: zodResolver(loginSchema),
  })
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const handleGoogleIdToken = async (idToken: string) => {
    setErrorMsg(null)
    try {
      const data = await googleLogin(idToken)
      const fullName = [data.user.first_name, data.user.last_name].filter(Boolean).join(' ').trim()
      const role = data.user.role || 'Guest'
      setAuth({
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        tokenType: data.token_type,
        sessionId: data.session_id,
        user: {
          id: data.user.id,
          email: data.user.email,
          role,
          name: fullName || undefined,
        },
      })
      navigate(defaultRouteForRole(normaliseRole(role)))
    } catch (err) {
      if (isAxiosError<{ detail?: string }>(err)) {
        setErrorMsg(err.response?.data?.detail || 'Google sign-in failed.')
      } else {
        setErrorMsg('Google sign-in failed.')
      }
    }
  }

  const onSubmit = async (data: LoginInput) => {
    setErrorMsg(null)
    try {
      const result = await login(data.email, data.password)
      if (result.requires2FA) {
        navigate('/2fa', { state: { tempToken: result.tempToken, email: data.email } })
        return
      }
      // success navigates inside useAuth.login (role-based redirect)
    } catch (err) {
      if (isAxiosError<{ detail?: string; requires_2fa?: boolean }>(err)) {
        const status = err.response?.status
        const detail = err.response?.data?.detail
        if (status === 401) {
          setErrorMsg('Invalid email or password.')
        } else if (status === 423) {
          setErrorMsg('Account is locked. Please contact support.')
        } else if (status === 429) {
          setErrorMsg(detail || 'Too many login attempts. Please try again later.')
        } else if (detail) {
          setErrorMsg(detail)
        } else {
          setErrorMsg('An unexpected error occurred. Please try again.')
        }
      } else {
        setErrorMsg('An unexpected error occurred. Please try again.')
      }
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md bg-white rounded-lg shadow-md p-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-6 text-center">Manager Login</h1>

        {errorMsg && (
          <div className="mb-4 p-3 bg-red-50 text-red-700 rounded border border-red-200" role="alert" aria-live="assertive">
            {errorMsg}
          </div>
        )}
        <LiveRegion message={errorMsg || ''} priority="assertive" />

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700">
              Email
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              aria-invalid={errors.email ? 'true' : 'false'}
              aria-describedby={errors.email ? 'email-error' : undefined}
              {...register('email')}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
            {errors.email && (
              <p className="mt-1 text-sm text-red-600" id="email-error" role="alert">{errors.email.message}</p>
            )}
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700">
              Password
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              aria-invalid={errors.password ? 'true' : 'false'}
              aria-describedby={errors.password ? 'password-error' : undefined}
              {...register('password')}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
            {errors.password && (
              <p className="mt-1 text-sm text-red-600" id="password-error" role="alert">{errors.password.message}</p>
            )}
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-2.5 px-4 bg-brand-600 text-white font-medium rounded-md hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            aria-busy={isSubmitting}
          >
            {isSubmitting ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <div className="mt-5 mb-3 flex items-center gap-3">
          <div className="h-px flex-1 bg-gray-200" />
          <span className="text-xs uppercase tracking-wider text-gray-400">or</span>
          <div className="h-px flex-1 bg-gray-200" />
        </div>
        <GoogleSignInButton
          onIdToken={handleGoogleIdToken}
          onError={(msg) => setErrorMsg(msg)}
        />

        <div className="mt-4 text-center">
          <p className="text-xs text-gray-500">
            Forgot your password? Contact your administrator to reset it.
          </p>
        </div>
      </div>
    </div>
  )
}
