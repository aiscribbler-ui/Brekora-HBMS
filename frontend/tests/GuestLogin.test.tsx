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
  googleLogin: vi.fn(),
}))

vi.mock('@/hooks/useGuestAuth', async () => {
  const actual = await vi.importActual<typeof import('@/hooks/useGuestAuth')>('@/hooks/useGuestAuth')
  return {
    ...actual,
    useGuestAuth: () => ({
      user: null,
      isAuthenticated: false,
      login: async (email: string, password: string) => {
        await mockPost({ email, password })
        return true
      },
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

function renderRoute(initialEntry = '/guest/login') {
  const testRouter = createMemoryRouter(routes, {
    initialEntries: [initialEntry],
  })
  return render(<RouterProvider router={testRouter} />)
}

describe('GuestLogin page', () => {
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
      expect(screen.getByText(/password is required/i)).toBeInTheDocument()
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

  it('submits credentials on success', async () => {
    mockPost.mockResolvedValue({
      access_token: 'token123',
      refresh_token: 'refresh123',
      token_type: 'bearer',
    })

    renderRoute()
    const user = userEvent.setup()
    await user.type(screen.getByLabelText(/email/i), 'guest@brekora.test')
    await user.type(screen.getByLabelText(/password/i), 'Password123')
    await user.click(screen.getByRole('button', { name: /^Sign In$/i }))

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith({
        email: 'guest@brekora.test',
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
    await user.type(screen.getByLabelText(/email/i), 'guest@brekora.test')
    await user.type(screen.getByLabelText(/password/i), 'WrongPass123')
    await user.click(screen.getByRole('button', { name: /^Sign In$/i }))

    await waitFor(() => {
      expect(screen.getByText(/invalid email or password/i)).toBeInTheDocument()
    })
  })

  it('navigates to signup page', async () => {
    renderRoute()
    const user = userEvent.setup()
    const signupLink = screen.getByText(/sign up/i)
    await user.click(signupLink)
    await waitFor(() => {
      expect(screen.getAllByText(/create account/i)[0]).toBeInTheDocument()
    })
  })

  it('renders google sign in fallback when client id missing', () => {
    renderRoute()
    expect(screen.getByText(/sign in with google/i)).toBeInTheDocument()
  })
})
