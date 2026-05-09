import { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import {
  HomeIcon,
  BuildingOfficeIcon,
  CalendarIcon,
  CubeIcon,
  InboxArrowDownIcon,
  BookOpenIcon,
  Cog6ToothIcon,
  Bars3Icon,
  XMarkIcon,
  ChartPieIcon,
  ChatBubbleLeftRightIcon,
} from '@heroicons/react/24/outline'

interface NavItem {
  to: string
  label: string
  icon: React.ElementType
  roles?: string[]
}

const navItems: NavItem[] = [
  { to: '/dashboard', label: 'Dashboard', icon: HomeIcon, roles: ['Admin', 'Manager', 'Owner', 'Partner', 'ListingManager'] },
  { to: '/properties', label: 'Properties', icon: BuildingOfficeIcon, roles: ['Admin', 'Manager', 'ListingManager'] },
  { to: '/calendar', label: 'Calendar', icon: CalendarIcon, roles: ['Admin', 'Manager', 'ListingManager'] },
  { to: '/packages', label: 'Packages', icon: CubeIcon, roles: ['Admin', 'Manager'] },
  { to: '/ota/queue', label: 'OTA Queue', icon: InboxArrowDownIcon, roles: ['Admin', 'Manager', 'ListingManager'] },
  { to: '/bookings/manual', label: 'New Booking', icon: BookOpenIcon, roles: ['Admin', 'Manager'] },
  { to: '/messages', label: 'Messages', icon: ChatBubbleLeftRightIcon, roles: ['Admin', 'Manager'] },
  { to: '/owner', label: 'Owner', icon: ChartPieIcon, roles: ['Owner', 'Admin', 'Manager'] },
  { to: '/admin', label: 'Admin', icon: Cog6ToothIcon, roles: ['Admin'] },
]

export default function Sidebar() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const { user, isAuthenticated } = useAuthStore()
  const location = useLocation()

  const isAuthPage =
    location.pathname === '/login' ||
    location.pathname === '/2fa' ||
    location.pathname.startsWith('/guest') ||
    location.pathname.startsWith('/book')

  if (isAuthPage || !isAuthenticated) return null

  const filtered = navItems.filter((item) => {
    if (!item.roles) return true
    return item.roles.includes(user?.role ?? '')
  })

  const sidebarContent = (
    <nav aria-label="Main navigation" className="flex-1 px-3 py-4 space-y-1">
      {filtered.map((item) => {
        const Icon = item.icon
        return (
          <NavLink
            key={item.to}
            to={item.to}
            onClick={() => setMobileOpen(false)}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                isActive
                  ? 'bg-brand-600 text-white shadow-md shadow-brand-200'
                  : 'text-gray-600 hover:bg-brand-50 hover:text-brand-700'
              }`
            }
          >
            <Icon className="h-5 w-5 shrink-0" aria-hidden="true" />
            {item.label}
          </NavLink>
        )
      })}
    </nav>
  )

  return (
    <>
      {/* Mobile hamburger */}
      <div className="lg:hidden fixed top-3 left-3 z-50">
        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="p-2 rounded-lg bg-white shadow-md border border-gray-200 text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-brand-500"
          aria-label={mobileOpen ? 'Close navigation' : 'Open navigation'}
        >
          {mobileOpen ? <XMarkIcon className="h-5 w-5" /> : <Bars3Icon className="h-5 w-5" />}
        </button>
      </div>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/30 z-40 lg:hidden"
          onClick={() => setMobileOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <aside
        aria-label="Sidebar"
        className={`fixed inset-y-0 left-0 z-40 w-64 bg-white border-r border-gray-200 flex flex-col transform transition-transform duration-300 lg:translate-x-0 lg:static lg:h-screen ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-5 py-4 border-b border-gray-100">
          <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shadow-sm">
            <span className="text-white font-bold text-sm">B</span>
          </div>
          <span className="text-lg font-bold bg-gradient-to-r from-brand-600 to-brand-800 bg-clip-text text-transparent">
            Brekora
          </span>
        </div>

        {sidebarContent}

        {/* User info */}
        <div className="px-5 py-4 border-t border-gray-100">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-full bg-brand-100 flex items-center justify-center text-brand-700 font-semibold text-xs">
              {(user?.name?.[0] ?? user?.email?.[0] ?? 'U').toUpperCase()}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">{user?.name || user?.email || 'User'}</p>
              <p className="text-xs text-gray-500 capitalize">{user?.role}</p>
            </div>
          </div>
        </div>
      </aside>
    </>
  )
}
