import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { LogOut, ShieldCheck } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { useAuth } from '@/hooks/useAuth'
import SkipLink from '@/components/a11y/SkipLink'
import Sidebar, { MobileMenuButton, useSidebarState } from '@/components/layout/Sidebar'

function App() {
  const { isAuthenticated, user } = useAuthStore()
  const { logout } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const sidebar = useSidebarState()
  const isStandalonePage =
    location.pathname === '/login' ||
    location.pathname === '/2fa' ||
    location.pathname.startsWith('/guest') ||
    location.pathname.startsWith('/book')

  if (isStandalonePage) {
    return (
      <div className="min-h-screen flex flex-col">
        <SkipLink />
        <main id="main-content" className="flex-1" tabIndex={-1}>
          <Outlet />
        </main>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex bg-gray-50">
      <SkipLink />
      <Sidebar
        collapsed={sidebar.collapsed}
        onToggle={sidebar.toggleCollapsed}
        mobileOpen={sidebar.mobileOpen}
        onMobileClose={sidebar.closeMobile}
      />
      <div className="flex-1 flex flex-col min-w-0">
        <header className="sticky top-0 z-20 bg-white/80 backdrop-blur border-b border-gray-200 px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MobileMenuButton onClick={sidebar.openMobile} />
            <h1 className="text-base font-semibold text-gray-900">Brekora BMS</h1>
          </div>
          {isAuthenticated && (
            <div className="flex items-center gap-1">
              {user && (
                <span className="hidden md:inline text-xs text-gray-500 mr-2">
                  {user.email}
                </span>
              )}
              <button
                onClick={() => navigate('/2fa/setup')}
                className="inline-flex items-center gap-1.5 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 px-3 py-1.5 rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
                title="Two-factor authentication"
              >
                <ShieldCheck className="w-4 h-4" />
                <span className="hidden sm:inline">Security</span>
              </button>
              <button
                onClick={logout}
                className="inline-flex items-center gap-1.5 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 px-3 py-1.5 rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
              >
                <LogOut className="w-4 h-4" />
                <span className="hidden sm:inline">Logout</span>
              </button>
            </div>
          )}
        </header>
        <main id="main-content" className="flex-1 p-4 md:p-6" tabIndex={-1}>
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export default App
