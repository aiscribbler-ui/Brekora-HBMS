import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Link, useNavigate } from 'react-router-dom'
import { useGuestAuth } from '@/hooks/useGuestAuth'
import { useGuestAuthStore } from '@/store/guestAuthStore'
import { loginSchema, type LoginInput } from '@/lib/validation'
import { isAxiosError } from '@/lib/api'
import { googleLogin } from '@/services/authApi'
import GoogleSignInButton from '@/components/auth/GoogleSignInButton'

export default function GuestLogin() {
  const { login } = useGuestAuth()
  const navigate = useNavigate()
  const setGuestAuth = useGuestAuthStore((s) => s.setAuth)
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
      setGuestAuth({
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        tokenType: data.token_type,
        sessionId: data.session_id,
        user: {
          id: data.user.id,
          email: data.user.email,
          role: data.user.role || 'Guest',
          name: fullName || undefined,
        },
      })
      navigate('/guest')
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
      await login(data.email, data.password)
      // success navigates to /guest inside useGuestAuth.login
    } catch (err) {
      if (isAxiosError<{ detail?: string }>(err)) {
        const status = err.response?.status
        const detail = err.response?.data?.detail
        if (status === 401) {
          setErrorMsg('Invalid email or password.')
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
    <div className="min-h-screen flex items-center justify-center bg-brand-50 px-4 py-8">
      <div className="w-full max-w-md bg-white rounded-xl shadow-lg p-6 sm:p-8">
        <div className="text-center mb-6">
          <h1 className="text-2xl font-bold text-brand-700 font-display">Welcome Back</h1>
          <p className="text-sm text-brand-700 mt-1">Sign in to your guest account</p>
        </div>

        {errorMsg && (
          <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg border border-red-200" role="alert">
            {errorMsg}
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <div>
            <label htmlFor="guest-email" className="block text-sm font-medium text-gray-700">
              Email
            </label>
            <input
              id="guest-email"
              type="email"
              autoComplete="email"
              {...register('email')}
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
            {errors.email && (
              <p className="mt-1 text-sm text-red-600" id="guest-email-error">
                {errors.email.message}
              </p>
            )}
          </div>

          <div>
            <label htmlFor="guest-password" className="block text-sm font-medium text-gray-700">
              Password
            </label>
            <input
              id="guest-password"
              type="password"
              autoComplete="current-password"
              {...register('password')}
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
            {errors.password && (
              <p className="mt-1 text-sm text-red-600" id="guest-password-error">
                {errors.password.message}
              </p>
            )}
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-2.5 px-4 bg-brand-600 text-white font-medium rounded-lg hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isSubmitting ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <div className="mt-5 mb-1 flex items-center gap-3">
          <div className="h-px flex-1 bg-gray-200" />
          <span className="text-xs uppercase tracking-wider text-gray-500">or</span>
          <div className="h-px flex-1 bg-gray-200" />
        </div>
        <div className="mt-4">
          <button
            type="button"
            onClick={() => { window.location.href = 'http://localhost:8000/api/v1/auth/google' }}
            className="w-full py-2.5 px-4 bg-white text-gray-700 font-medium rounded-lg border border-gray-300 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 transition-colors flex items-center justify-center gap-2"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" />
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
            </svg>
            Sign in with Google
          </button>
        </div>

        <div className="mt-6 text-center space-y-2">
          <p className="text-sm text-gray-600">
            Don&apos;t have an account?{' '}
            <Link to="/guest/signup" className="text-brand-600 hover:text-brand-700 hover:underline font-medium">
              Sign up
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
