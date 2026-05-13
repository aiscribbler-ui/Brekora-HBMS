import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type Theme = 'light' | 'dark' | 'system'
type ResolvedTheme = 'light' | 'dark'

interface ThemeState {
  theme: Theme
  resolvedTheme: ResolvedTheme
  setTheme: (theme: Theme) => void
  toggleTheme: () => void
}

function getSystemTheme(): ResolvedTheme {
  if (typeof window === 'undefined') return 'light'
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function applyThemeClass(resolved: ResolvedTheme) {
  const root = document.documentElement
  if (resolved === 'dark') {
    root.classList.add('dark')
  } else {
    root.classList.remove('dark')
  }
}

const safeStorage = {
  getItem: (name: string) => {
    try {
      return localStorage.getItem(name)
    } catch {
      return null
    }
  },
  setItem: (name: string, value: string) => {
    try {
      localStorage.setItem(name, value)
    } catch {
      // silently fail in private mode
    }
  },
  removeItem: (name: string) => {
    try {
      localStorage.removeItem(name)
    } catch {
      // silently fail in private mode
    }
  },
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      theme: 'system',
      resolvedTheme: getSystemTheme(),
      setTheme: (theme) => {
        const resolved = theme === 'system' ? getSystemTheme() : theme
        set({ theme, resolvedTheme: resolved })
        applyThemeClass(resolved)
      },
      toggleTheme: () => {
        const current = get().resolvedTheme
        const next = current === 'dark' ? 'light' : 'dark'
        set({ theme: next, resolvedTheme: next })
        applyThemeClass(next)
      },
    }),
    {
      name: 'brekora-theme',
      storage: safeStorage as any,
      partialize: (state) => ({ theme: state.theme }) as any,
      onRehydrateStorage: () => (state) => {
        if (!state) return
        const resolved = state.theme === 'system' ? getSystemTheme() : state.theme
        state.resolvedTheme = resolved
        applyThemeClass(resolved)
      },
    },
  ),
)

// Listen for system preference changes when theme is 'system'
if (typeof window !== 'undefined') {
  const mql = window.matchMedia('(prefers-color-scheme: dark)')
  mql.addEventListener('change', (e) => {
    const store = useThemeStore.getState()
    if (store.theme === 'system') {
      const resolved = e.matches ? 'dark' : 'light'
      useThemeStore.setState({ resolvedTheme: resolved })
      applyThemeClass(resolved)
    }
  })
}
