import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User } from '@/store/authStore'

export interface GuestAuthTokens {
  accessToken: string
  refreshToken: string
  tokenType: string
  sessionId?: string | null
}

interface GuestAuthState extends GuestAuthTokens {
  user: User | null
  isAuthenticated: boolean
  setAuth: (tokens: GuestAuthTokens & { user: User }) => void
  clearAuth: () => void
}

const initialState: Omit<GuestAuthState, 'setAuth' | 'clearAuth'> = {
  accessToken: '',
  refreshToken: '',
  tokenType: '',
  sessionId: null,
  user: null,
  isAuthenticated: false,
}

export const useGuestAuthStore = create<GuestAuthState>()(
  persist(
    (set) => ({
      ...initialState,
      setAuth: ({ accessToken, refreshToken, tokenType, sessionId, user }) =>
        set({
          accessToken,
          refreshToken,
          tokenType,
          sessionId: sessionId ?? null,
          user,
          isAuthenticated: true,
        }),
      clearAuth: () => set({ ...initialState }),
    }),
    {
      name: 'brekora-guest-auth',
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        tokenType: state.tokenType,
        sessionId: state.sessionId,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    },
  ),
)
