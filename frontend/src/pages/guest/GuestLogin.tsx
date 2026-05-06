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
    <div className="min-h-screen flex items-center justify-center bg-teal-50 px-4 py-8">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-lg p-6 sm:p-8">
        <div className="text-center mb-6">
          <h1 className="text-2xl font-bold text-teal-800">Welcome Back</h1>
          <p className="text-sm text-teal-600 mt-1">Sign in to your guest account</p>
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
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 shadow-sm focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
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
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 shadow-sm focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
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
            className="w-full py-2.5 px-4 bg-teal-600 text-white font-medium rounded-lg hover:bg-teal-700 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isSubmitting ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <div className="mt-5 mb-1 flex items-center gap-3">
          <div className="h-px flex-1 bg-gray-200" />
          <span className="text-xs uppercase tracking-wider text-gray-400">or</span>
          <div className="h-px flex-1 bg-gray-200" />
        </div>
        <div className="mt-4">
          <GoogleSignInButton
            onIdToken={handleGoogleIdToken}
            onError={(msg) => setErrorMsg(msg)}
          />
        </div>

        <div className="mt-6 text-center space-y-2">
          <p className="text-sm text-gray-600">
            Don&apos;t have an account?{' '}
            <Link to="/guest/signup" className="text-teal-600 hover:text-teal-700 hover:underline font-medium">
              Sign up
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
