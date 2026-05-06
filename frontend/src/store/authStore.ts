import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface User {
  id: string
  email: string
  role: string
  name?: string
  org_id?: string
}

export interface AuthTokens {
  accessToken: string
  refreshToken: string
  tokenType: string
}

interface AuthState extends AuthTokens {
  user: User | null
  isAuthenticated: boolean
  setAuth: (tokens: AuthTokens & { user: User }) => void
  clearAuth: () => void
}

const initialState: Omit<AuthState, 'setAuth' | 'clearAuth'> = {
  accessToken: '',
  refreshToken: '',
  tokenType: '',
  user: null,
  isAuthenticated: false,
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      ...initialState,
      setAuth: ({ accessToken, refreshToken, tokenType, user }) =>
        set({
          accessToken,
          refreshToken,
          tokenType,
          user,
          isAuthenticated: true,
        }),
      clearAuth: () => set({ ...initialState }),
    }),
    {
      name: 'brekora-auth',
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        tokenType: state.tokenType,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    },
  ),
)
