import { Outlet, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { useAuth } from '@/hooks/useAuth'
import SkipLink from '@/components/a11y/SkipLink'

function App() {
  const { isAuthenticated } = useAuthStore()
  const { logout } = useAuth()
  const location = useLocation()
  const isAuthPage =
    location.pathname === '/login' ||
    location.pathname === '/2fa' ||
    location.pathname.startsWith('/guest')

  return (
    <div className="min-h-screen flex flex-col">
      <SkipLink />
      {!isAuthPage && (
        <header className="bg-brand-600 text-white px-4 py-3 shadow flex items-center justify-between">
          <h1 className="text-lg font-semibold">Brekora BMS</h1>
          {isAuthenticated && (
            <button
              onClick={logout}
              className="text-sm bg-brand-700 hover:bg-brand-800 px-3 py-1.5 rounded transition-colors focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 focus:ring-offset-brand-600"
            >
              Logout
            </button>
          )}
        </header>
      )}
      <main id="main-content" className={isAuthPage ? 'flex-1' : 'flex-1 p-4'} tabIndex={-1}>
        <Outlet />
      </main>
    </div>
  )
}

export default App
