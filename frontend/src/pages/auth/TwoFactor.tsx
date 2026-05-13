import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { twoFactorSchema, type TwoFactorInput } from '@/lib/validation'
import { api } from '@/lib/api'
import { useAuthStore } from '@/store/authStore'
import { useAuth } from '@/hooks/useAuth'

export default function TwoFactor() {
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams] = useSearchParams()
  const { verify2FA } = useAuth()
  const state = (location.state as LocationState | null) ?? null
  const tempToken = state?.tempToken ?? null
  const email = state?.email || searchParams.get('email') || ''
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<TwoFactorInput>({
    resolver: zodResolver(twoFactorSchema),
  })

  const onSubmit = async (data: TwoFactorInput) => {
    setErrorMsg(null)
    try {
      const tempToken = searchParams.get('temp_token')
      if (!tempToken) {
        setErrorMsg('Missing temporary token. Please log in again.')
        return
      }
      const response = await api.post('/auth/2fa/login-verify', {
        temp_token: tempToken,
        token: data.code,
      })
      const { access_token, refresh_token, token_type, user } = response.data
      useAuthStore.getState().setAuth({
        accessToken: access_token,
        refreshToken: refresh_token,
        tokenType: token_type || 'bearer',
        user: user || { id: '', email, role: 'Admin' },
      })
      navigate('/dashboard')
    } catch (err: any) {
      if (err.response?.status === 401) {
        setErrorMsg('Invalid code. Please try again.')
      } else {
        setErrorMsg(err.response?.data?.detail || 'Verification failed.')
      }
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 px-4">
      <div className="w-full max-w-md bg-white dark:bg-gray-800 rounded-lg shadow-md p-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2 text-center">Two-Factor Authentication</h1>
        <p className="text-sm text-gray-600 dark:text-gray-300 mb-1 text-center">
          Enter the 6-digit code from your authenticator app.
        </p>
        {email && (
          <p className="text-sm text-brand-600 mb-6 text-center font-medium">{email}</p>
        )}

        {errorMsg && (
          <div className="mb-4 p-3 bg-amber-50 dark:bg-amber-900/20 text-amber-800 dark:text-amber-400 rounded border border-amber-200 dark:border-amber-800" role="alert">
            {errorMsg}
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <div>
            <label htmlFor="code" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Authenticator Code
            </label>
            <input
              id="code"
              type="text"
              inputMode="numeric"
              maxLength={6}
              autoComplete="one-time-code"
              placeholder="000000"
              {...register('code')}
              className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 shadow-sm text-center tracking-widest font-mono focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
            {errors.code && (
              <p className="mt-1 text-sm text-red-600" id="code-error">{errors.code.message}</p>
            )}
          </div>

          <button
            type="submit"
            disabled={isSubmitting || !tempToken}
            className="w-full py-2.5 px-4 bg-brand-600 text-white font-medium rounded-md hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isSubmitting ? 'Verifying...' : 'Verify'}
          </button>
        </form>

        <div className="mt-4 text-center">
          <button
            type="button"
            onClick={() => navigate('/login')}
            className="text-sm text-brand-600 hover:text-brand-700 hover:underline"
          >
            Back to login
          </button>
        </div>
      </div>
    </div>
  )
}
