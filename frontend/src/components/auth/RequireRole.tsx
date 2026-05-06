import { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { useGuestAuthStore } from '@/store/guestAuthStore'
import { hasRole, type Role } from '@/lib/roles'

interface RequireRoleProps {
  allowed: readonly Role[]
  children: ReactNode
  redirectTo?: string
}

export default function RequireRole({ allowed, children, redirectTo = '/login' }: RequireRoleProps) {
  const manager = useAuthStore()
  const guest = useGuestAuthStore()
  const location = useLocation()

  const allowsGuest = allowed.includes('Guest')
  const active = allowsGuest && guest.isAuthenticated && guest.user
    ? guest
    : manager.isAuthenticated && manager.user
      ? manager
      : null

  if (!active || !active.user) {
    return <Navigate to={redirectTo} state={{ from: location.pathname }} replace />
  }
  if (!hasRole(active.user.role, allowed)) {
    return (
      <div className="flex min-h-screen items-center justify-center px-4">
        <div className="text-center max-w-md">
          <h1 className="text-2xl font-bold text-gray-900">Access denied</h1>
          <p className="mt-2 text-sm text-gray-600">
            You do not have permission to view this page.
          </p>
        </div>
      </div>
    )
  }
  return <>{children}</>
}
