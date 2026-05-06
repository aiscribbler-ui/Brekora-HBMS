import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { AxiosError } from 'axios'
import { routes } from '@/router'

const mockPost = vi.fn()
const mockNavigate = vi.fn()

vi.mock('@/services/authApi', () => ({
  login: (...args: unknown[]) => mockPost(...args),
  logout: vi.fn(),
  refreshToken: vi.fn(),
  verifyTwoFactorLogin: vi.fn(),
  googleLogin: vi.fn(),
  getMe: vi.fn().mockRejectedValue(new Error('not authenticated')),
}))

vi.mock('@/hooks/useAuth', async () => {
  const actual = await vi.importActual<typeof import('@/hooks/useAuth')>('@/hooks/useAuth')
  return {
    ...actual,
    useAuth: () => ({
      user: null,
      isAuthenticated: false,
      sessionId: null,
      login: async (email: string, password: string) => {
        const data = await mockPost({ email, password })
        if (data.requires_2fa) {
          return { success: false, requires2FA: true, tempToken: data.temp_token ?? null }
        }
        return { success: true, requires2FA: false }
      },
      verify2FA: vi.fn(),
      logout: vi.fn(),
    }),
  }
})

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

function renderRoute(initialEntry = '/login') {
  const testRouter = createMemoryRouter(routes, {
    initialEntries: [initialEntry],
  })
  return render(<RouterProvider router={testRouter} />)
}

describe('Login page', () => {
  beforeEach(() => {
    mockPost.mockReset()
    mockNavigate.mockReset()
    localStorage.clear()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('renders email and password inputs', () => {
    renderRoute()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^Sign In$/i })).toBeInTheDocument()
  })

  it('shows validation errors for empty fields', async () => {
    renderRoute()
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /^Sign In$/i }))
    await waitFor(() => {
      expect(screen.getByText(/email is required/i)).toBeInTheDocument()
      expect(screen.getByText(/password must be at least 8 characters/i)).toBeInTheDocument()
    })
  })

  it('shows validation error for invalid email', async () => {
    renderRoute()
    const user = userEvent.setup()
    await user.type(screen.getByLabelText(/email/i), 'not-an-email')
    await user.type(screen.getByLabelText(/password/i), 'password123')
    await user.click(screen.getByRole('button', { name: /^Sign In$/i }))
    await waitFor(() => {
      expect(screen.getByText(/invalid email address/i)).toBeInTheDocument()
    })
  })

  it('submits credentials and redirects on success', async () => {
    mockPost.mockResolvedValue({
      access_token: 'token123',
      refresh_token: 'refresh123',
      token_type: 'bearer',
    })

    renderRoute()
    const user = userEvent.setup()
    await user.type(screen.getByLabelText(/email/i), 'manager@brekora.test')
    await user.type(screen.getByLabelText(/password/i), 'Password123')
    await user.click(screen.getByRole('button', { name: /^Sign In$/i }))

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith({
        email: 'manager@brekora.test',
        password: 'Password123',
      })
    })
  })

  it('shows invalid credentials error on 401', async () => {
    const error = new AxiosError(
      'Request failed',
      undefined,
      undefined,
      undefined,
      { status: 401, data: { detail: 'Invalid credentials' }, headers: {}, config: {} } as unknown as import('axios').AxiosResponse,
    )
    mockPost.mockRejectedValue(error)

    renderRoute()
    const user = userEvent.setup()
    await user.type(screen.getByLabelText(/email/i), 'manager@brekora.test')
    await user.type(screen.getByLabelText(/password/i), 'WrongPass123')
    await user.click(screen.getByRole('button', { name: /^Sign In$/i }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/invalid email or password/i)
    })
  })

  it('shows account locked error on 423', async () => {
    const error = new AxiosError(
      'Request failed',
      undefined,
      undefined,
      undefined,
      { status: 423, data: { detail: 'Account locked' }, headers: {}, config: {} } as unknown as import('axios').AxiosResponse,
    )
    mockPost.mockRejectedValue(error)

    renderRoute()
    const user = userEvent.setup()
    await user.type(screen.getByLabelText(/email/i), 'locked@brekora.test')
    await user.type(screen.getByLabelText(/password/i), 'Password123')
    await user.click(screen.getByRole('button', { name: /^Sign In$/i }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/account is locked/i)
    })
  })

  it('redirects to 2fa page with temp_token when 2fa is required', async () => {
    mockPost.mockResolvedValue({
      access_token: null,
      refresh_token: null,
      token_type: 'bearer',
      requires_2fa: true,
      temp_token: 'temp-abc',
    })

    renderRoute()
    const user = userEvent.setup()
    await user.type(screen.getByLabelText(/email/i), '2fa@brekora.test')
    await user.type(screen.getByLabelText(/password/i), 'Password123')
    await user.click(screen.getByRole('button', { name: /^Sign In$/i }))

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/2fa', {
        state: { tempToken: 'temp-abc', email: '2fa@brekora.test' },
      })
    })
  })

  it('renders forgot password helper text', () => {
    renderRoute()
    expect(screen.getByText(/forgot your password/i)).toBeInTheDocument()
  })
})

describe('TwoFactor page', () => {
  it('renders code input and verify button', () => {
    renderRoute('/2fa?email=test%40brekora.test')
    expect(screen.getByLabelText(/authenticator code/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /verify/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /back to login/i })).toBeInTheDocument()
  })

  it('warns when reached without temp_token', async () => {
    renderRoute('/2fa?email=test%40brekora.test')
    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/sign-in session expired/i)
    })
  })
})
