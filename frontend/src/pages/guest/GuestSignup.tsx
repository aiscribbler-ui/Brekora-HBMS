import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Link, useNavigate } from 'react-router-dom'
import { guestSignupSchema, type GuestSignupInput } from '@/lib/validation'
import { signupGuest } from '@/services/guestApi'
import { useGuestAuthStore } from '@/store/guestAuthStore'
import { isAxiosError } from '@/lib/api'

export default function GuestSignup() {
  const navigate = useNavigate()
  const setAuth = useGuestAuthStore((s) => s.setAuth)
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<GuestSignupInput>({
    resolver: zodResolver(guestSignupSchema),
  })
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const onSubmit = async (data: GuestSignupInput) => {
    setErrorMsg(null)
    try {
      const response = await signupGuest({
        first_name: data.firstName,
        last_name: data.lastName,
        email: data.email,
        phone: data.phone || undefined,
        password: data.password,
      })
      setAuth({
        accessToken: response.access_token,
        refreshToken: response.refresh_token,
        tokenType: response.token_type,
        sessionId: response.session_id,
        user: {
          id: '',
          email: data.email,
          role: 'Guest',
          name: `${data.firstName} ${data.lastName}`.trim(),
        },
      })
      navigate('/guest')
    } catch (err) {
      if (isAxiosError<{ detail?: string }>(err)) {
        const status = err.response?.status
        const detail = err.response?.data?.detail
        if (status === 409) {
          setErrorMsg(detail || 'An account with this email already exists.')
        } else if (detail) {
          setErrorMsg(detail)
        } else {
          setErrorMsg('Could not create your account. Please try again.')
        }
      } else {
        setErrorMsg('Could not create your account. Please try again.')
      }
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-teal-50 px-4 py-8">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-lg p-6 sm:p-8">
        <div className="text-center mb-6">
          <h1 className="text-2xl font-bold text-teal-800">Create Account</h1>
          <p className="text-sm text-teal-600 mt-1">Join us for a seamless booking experience</p>
        </div>

        {errorMsg && (
          <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg border border-red-200" role="alert">
            {errorMsg}
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="firstName" className="block text-sm font-medium text-gray-700">
                First name
              </label>
              <input
                id="firstName"
                type="text"
                autoComplete="given-name"
                {...register('firstName')}
                className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 shadow-sm focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
              />
              {errors.firstName && (
                <p className="mt-1 text-sm text-red-600" id="firstName-error">
                  {errors.firstName.message}
                </p>
              )}
            </div>

            <div>
              <label htmlFor="lastName" className="block text-sm font-medium text-gray-700">
                Last name
              </label>
              <input
                id="lastName"
                type="text"
                autoComplete="family-name"
                {...register('lastName')}
                className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 shadow-sm focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
              />
              {errors.lastName && (
                <p className="mt-1 text-sm text-red-600" id="lastName-error">
                  {errors.lastName.message}
                </p>
              )}
            </div>
          </div>

          <div>
            <label htmlFor="signup-email" className="block text-sm font-medium text-gray-700">
              Email
            </label>
            <input
              id="signup-email"
              type="email"
              autoComplete="email"
              {...register('email')}
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 shadow-sm focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
            />
            {errors.email && (
              <p className="mt-1 text-sm text-red-600" id="signup-email-error">
                {errors.email.message}
              </p>
            )}
          </div>

          <div>
            <label htmlFor="phone" className="block text-sm font-medium text-gray-700">
              Phone <span className="text-gray-400 font-normal">(optional)</span>
            </label>
            <input
              id="phone"
              type="tel"
              autoComplete="tel"
              {...register('phone')}
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 shadow-sm focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
            />
            {errors.phone && (
              <p className="mt-1 text-sm text-red-600" id="phone-error">
                {errors.phone.message}
              </p>
            )}
          </div>

          <div>
            <label htmlFor="signup-password" className="block text-sm font-medium text-gray-700">
              Password
            </label>
            <input
              id="signup-password"
              type="password"
              autoComplete="new-password"
              {...register('password')}
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 shadow-sm focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
            />
            {errors.password && (
              <p className="mt-1 text-sm text-red-600" id="signup-password-error">
                {errors.password.message}
              </p>
            )}
          </div>

          <div>
            <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700">
              Confirm password
            </label>
            <input
              id="confirmPassword"
              type="password"
              autoComplete="new-password"
              {...register('confirmPassword')}
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 shadow-sm focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
            />
            {errors.confirmPassword && (
              <p className="mt-1 text-sm text-red-600" id="confirmPassword-error">
                {errors.confirmPassword.message}
              </p>
            )}
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-2.5 px-4 bg-teal-600 text-white font-medium rounded-lg hover:bg-teal-700 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isSubmitting ? 'Creating account...' : 'Create Account'}
          </button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-sm text-gray-600">
            Already have an account?{' '}
            <Link to="/guest/login" className="text-teal-600 hover:text-teal-700 hover:underline font-medium">
              Log in
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
