import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Building2,
  Calendar,
  Package,
  Inbox,
  BookOpen,
  UserCircle,
  Shield,
  ChevronLeft,
  Menu,
  X,
} from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { hasRole, type Role } from '@/lib/roles'

interface NavItem {
  to: string
  label: string
  icon: typeof LayoutDashboard
  roles: readonly Role[]
}

const navItems: NavItem[] = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard, roles: ['Manager', 'Admin', 'Owner'] },
  { to: '/properties', label: 'Properties', icon: Building2, roles: ['Manager', 'Admin'] },
  { to: '/calendar', label: 'Calendar', icon: Calendar, roles: ['Manager', 'Admin'] },
  { to: '/packages', label: 'Packages', icon: Package, roles: ['Manager', 'Admin'] },
  { to: '/ota/queue', label: 'OTA Queue', icon: Inbox, roles: ['Manager', 'Admin'] },
  { to: '/bookings/manual', label: 'Bookings', icon: BookOpen, roles: ['Manager', 'Admin'] },
  { to: '/owner', label: 'Owner', icon: UserCircle, roles: ['Owner', 'Admin'] },
  { to: '/admin', label: 'Admin', icon: Shield, roles: ['Admin'] },
]

interface SidebarProps {
  collapsed: boolean
  onToggle: () => void
  mobileOpen: boolean
  onMobileClose: () => void
}

export default function Sidebar({ collapsed, onToggle, mobileOpen, onMobileClose }: SidebarProps) {
  const user = useAuthStore((s) => s.user)
  const visibleNavItems = navItems.filter((item) => hasRole(user?.role, item.roles))
  return (
    <>
      {mobileOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/40 md:hidden"
          onClick={onMobileClose}
          aria-hidden="true"
        />
      )}
      <aside
        className={`
          fixed md:static inset-y-0 left-0 z-40 flex flex-col
          bg-white border-r border-gray-200 shadow-sm
          transform transition-all duration-200 ease-in-out
          ${mobileOpen ? 'translate-x-0' : '-translate-x-full'} md:translate-x-0
          ${collapsed ? 'md:w-16' : 'md:w-60'}
          w-60
        `}
        aria-label="Primary navigation"
      >
        <div className={`flex items-center ${collapsed ? 'md:justify-center' : 'justify-between'} px-4 h-14 border-b border-gray-100`}>
          <div className={`flex items-center gap-2 ${collapsed ? 'md:hidden' : ''}`}>
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center text-white font-bold shadow-sm">
              B
            </div>
            <span className="font-semibold text-gray-900">Brekora</span>
          </div>
          {collapsed && (
            <div className="hidden md:flex w-8 h-8 rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 items-center justify-center text-white font-bold shadow-sm">
              B
            </div>
          )}
          <button
            onClick={onMobileClose}
            className="md:hidden p-1.5 rounded-md text-gray-500 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-brand-500"
            aria-label="Close navigation"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-1">
          {visibleNavItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              onClick={onMobileClose}
              className={({ isActive }) =>
                `group flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-1 ${
                  isActive
                    ? 'bg-brand-50 text-brand-700'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                }`
              }
              title={collapsed ? label : undefined}
            >
              {({ isActive }) => (
                <>
                  <Icon
                    className={`w-5 h-5 flex-shrink-0 ${isActive ? 'text-brand-600' : 'text-gray-400 group-hover:text-gray-600'}`}
                  />
                  <span className={collapsed ? 'md:hidden' : ''}>{label}</span>
                  {isActive && (
                    <span
                      className={`ml-auto w-1.5 h-1.5 rounded-full bg-brand-600 ${collapsed ? 'md:hidden' : ''}`}
                      aria-hidden="true"
                    />
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="hidden md:block border-t border-gray-100 p-2">
          <button
            onClick={onToggle}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-xs font-medium text-gray-500 hover:bg-gray-50 hover:text-gray-700 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500"
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            <ChevronLeft className={`w-4 h-4 transition-transform ${collapsed ? 'rotate-180' : ''}`} />
            <span className={collapsed ? 'md:hidden' : ''}>Collapse</span>
          </button>
        </div>
      </aside>
    </>
  )
}

export function MobileMenuButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="md:hidden p-2 rounded-md text-gray-600 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-brand-500"
      aria-label="Open navigation"
    >
      <Menu className="w-5 h-5" />
    </button>
  )
}

export function useSidebarState() {
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  return {
    collapsed,
    mobileOpen,
    toggleCollapsed: () => setCollapsed((v) => !v),
    openMobile: () => setMobileOpen(true),
    closeMobile: () => setMobileOpen(false),
  }
}
