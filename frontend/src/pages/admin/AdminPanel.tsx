import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { hasRole } from '@/lib/roles'
import FeatureFlags from '@/components/admin/FeatureFlags'
import SystemSettings from '@/components/admin/SystemSettings'
import UserManagement from '@/components/admin/UserManagement'
import OtaSettings from '@/components/admin/OtaSettings'

const tabs = [
  { id: 'feature-flags', label: 'Feature Flags', component: FeatureFlags },
  { id: 'system-settings', label: 'System Settings', component: SystemSettings },
  { id: 'user-management', label: 'User Management', component: UserManagement },
  { id: 'ota-settings', label: 'OTA Settings', component: OtaSettings },
] as const

type TabId = (typeof tabs)[number]['id']

export default function AdminPanel() {
  const user = useAuthStore((s) => s.user)
  const navigate = useNavigate()
  const location = useLocation()
  const [activeTab, setActiveTab] = useState<TabId>('feature-flags')

  useEffect(() => {
    const path = location.pathname.replace('/admin/', '').replace('/admin', '')
    if (path && tabs.some((t) => t.id === path)) {
      setActiveTab(path as TabId)
    }
  }, [location.pathname])

  useEffect(() => {
    if (!hasRole(user?.role, ['Admin'])) {
      const timer = setTimeout(() => navigate('/', { replace: true }), 3000)
      return () => clearTimeout(timer)
    }
  }, [user, navigate])

  if (!hasRole(user?.role, ['Admin'])) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900">Access Denied</h1>
          <p className="mt-2 text-gray-600">You do not have permission to view this page.</p>
          <p className="mt-1 text-sm text-gray-500">Redirecting to home...</p>
          <button
            onClick={() => navigate('/')}
            className="mt-4 inline-flex rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            Go Home
          </button>
        </div>
      </div>
    )
  }

  const ActiveComponent = tabs.find((t) => t.id === activeTab)?.component || FeatureFlags

  const handleTabChange = (id: TabId) => {
    setActiveTab(id)
    navigate(`/admin/${id}`)
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <h1 className="text-2xl font-bold text-gray-900">Admin Panel</h1>
        <div className="mt-6 flex flex-col gap-6 md:flex-row">
          {/* Mobile: horizontal scrollable top tabs; Desktop: sidebar */}
          <nav className="shrink-0 overflow-x-auto border-b border-gray-200 pb-2 md:w-64 md:border-b-0 md:border-r md:pr-4 md:pb-0">
            <div className="flex gap-1 md:flex-col">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => handleTabChange(tab.id)}
                  className={`whitespace-nowrap rounded-md px-4 py-2 text-left text-sm font-medium transition-colors ${
                    activeTab === tab.id
                      ? 'bg-brand-50 text-brand-700'
                      : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </nav>
          <main className="flex-1">
            <div className="rounded-lg bg-white p-6 shadow-sm">
              <ActiveComponent />
            </div>
          </main>
        </div>
      </div>
    </div>
  )
}
