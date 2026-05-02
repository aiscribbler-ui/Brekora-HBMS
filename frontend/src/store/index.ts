import { create } from 'zustand'
import { devtools } from 'zustand/middleware'

export { useAuthStore } from './authStore'
export type { User, AuthTokens } from './authStore'

interface UIState {
  sidebarOpen: boolean
  toggleSidebar: () => void
}

export const useUIStore = create<UIState>()(
  devtools(
    (set) => ({
      sidebarOpen: false,
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
    }),
    { name: 'ui-store' },
  ),
)
