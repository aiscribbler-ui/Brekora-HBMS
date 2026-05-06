import { Outlet, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { useAuth } from '@/hooks/useAuth'
import SkipLink from '@/components/a11y/SkipLink'
import Sidebar from '@/components/layout/Sidebar'

function App() {
  const { isAuthenticated } = useAuthStore()
  const { logout } = useAuth()
  const location = useLocation()
  const isAuthPage =
    location.pathname === '/login' ||
    location.pathname === '/2fa' ||
    location.pathname.startsWith('/guest') ||
    location.pathname.startsWith('/book')

  return (
    <div className="min-h-screen flex">
      <SkipLink />
      <Sidebar />
      <div className={`flex-1 flex flex-col min-h-screen transition-all ${!isAuthPage && isAuthenticated ? 'lg:ml-64' : ''}`}>
        {!isAuthPage && isAuthenticated && (
          <header className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between sticky top-0 z-30">
            <h1 className="text-lg font-semibold text-gray-900 lg:hidden">Brekora BMS</h1>
            <div className="flex-1" />
            <button
              onClick={logout}
              className="text-sm bg-brand-600 hover:bg-brand-700 text-white px-3 py-1.5 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
            >
              Logout
            </button>
          </header>
        )}
        <main id="main-content" className={isAuthPage ? 'flex-1' : 'flex-1 p-4 lg:p-6'} tabIndex={-1}>
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export default App
