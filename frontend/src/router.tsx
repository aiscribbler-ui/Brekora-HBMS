import { createBrowserRouter, type RouteObject, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import App from '@/App'
import { AuthGuard } from '@/components/auth/AuthGuard'
import { RoleGuard } from '@/components/auth/RoleGuard'
import RequireRole from '@/components/auth/RequireRole'
import Login from '@/pages/auth/Login'
import Setup from '@/pages/auth/Setup'
import TwoFactor from '@/pages/auth/TwoFactor'
import TwoFactorEnrol from '@/pages/auth/TwoFactorEnrol'
import ManagerDashboard from '@/pages/dashboard/ManagerDashboard'
import GuestLogin from '@/pages/guest/GuestLogin'
import GuestSignup from '@/pages/guest/GuestSignup'
import GuestDashboard from '@/pages/guest/GuestDashboard'
import MyBookings from '@/pages/guest/MyBookings'
import GuestProfile from '@/pages/guest/GuestProfile'
import PropertyList from '@/pages/properties/PropertyList'
import PropertyDetail from '@/pages/properties/PropertyDetail'
import RoomTypeList from '@/pages/properties/RoomTypeList'
import RoomTypeForm from '@/pages/properties/RoomTypeForm'
import CalendarGrid from '@/pages/calendar/CalendarGrid'
import PackageList from '@/pages/packages/PackageList'
import PackageBuilder from '@/pages/packages/PackageBuilder'
import OtaQueue from '@/pages/ota/OtaQueue'
import OtaMappings from '@/pages/ota/OtaMappings'
import MessageGuest from '@/pages/messages/MessageGuest'
import ManualBookingForm from '@/pages/bookings/ManualBookingForm'
import BookingDetail from '@/pages/bookings/BookingDetail'
import BookingEdit from '@/pages/bookings/BookingEdit'
import Landing from '@/pages/public/Landing'
import SearchResults from '@/pages/public/SearchResults'
import BookingFlow from '@/pages/public/BookingFlow'
import BookingConfirmation from '@/pages/public/BookingConfirmation'
import AdminPanel from '@/pages/admin/AdminPanel'
import OwnerDashboard from '@/pages/owner/OwnerDashboard'

const STAFF_OR_OWNER = ['Admin', 'Manager', 'Owner'] as const
const ALL_STAFF = ['Admin', 'Manager', 'Owner', 'Partner', 'ListingManager'] as const

function SetupRedirect() {
  const navigate = useNavigate()
  const [checked, setChecked] = useState(false)

  useEffect(() => {
    let cancelled = false
    api
      .get<{ setup_required: boolean }>('/auth/setup-status')
      .then((res) => {
        if (!cancelled) {
          setChecked(true)
          if (res.data.setup_required) {
            navigate('/setup', { replace: true })
          } else {
            navigate('/dashboard', { replace: true })
          }
        }
      })
      .catch(() => {
        if (!cancelled) {
          setChecked(true)
          navigate('/dashboard', { replace: true })
        }
      })
    return () => { cancelled = true }
  }, [navigate])

  if (!checked) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-pulse h-8 w-8 rounded-full bg-brand-600" />
      </div>
    )
  }
  return null
}

export const routes: RouteObject[] = [
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <SetupRedirect /> },
      {
        path: 'dashboard',
        element: (
          <RequireRole allowed={ALL_STAFF}>
            <ManagerDashboard />
          </RequireRole>
        ),
      },
      {
        path: 'setup',
        element: <Setup />,
      },
      {
        path: 'login',
        element: <Login />,
      },
      {
        path: '2fa',
        element: <TwoFactor />,
      },
      {
        path: '2fa/setup',
        element: (
          <RequireRole allowed={STAFF_OR_OWNER}>
            <TwoFactorEnrol />
          </RequireRole>
        ),
      },
      {
        path: 'properties',
        element: (
          <AuthGuard>
            <PropertyList />
          </AuthGuard>
        ),
      },
      {
        path: 'properties/:id',
        element: (
          <AuthGuard>
            <PropertyDetail />
          </AuthGuard>
        ),
      },
      {
        path: 'properties/:id/room-types',
        element: (
          <AuthGuard>
            <RoomTypeList />
          </AuthGuard>
        ),
      },
      {
        path: 'properties/:id/room-types/:roomTypeId',
        element: (
          <AuthGuard>
            <RoomTypeForm />
          </AuthGuard>
        ),
      },
      {
        path: 'calendar',
        element: (
          <AuthGuard>
            <CalendarGrid />
          </AuthGuard>
        ),
      },
      {
        path: 'packages',
        element: (
          <AuthGuard>
            <PackageList />
          </AuthGuard>
        ),
      },
      {
        path: 'packages/:id',
        element: (
          <AuthGuard>
            <PackageBuilder />
          </AuthGuard>
        ),
      },
      {
        path: 'ota/queue',
        element: (
          <AuthGuard>
            <OtaQueue />
          </AuthGuard>
        ),
      },
      {
        path: 'ota/mappings',
        element: (
          <AuthGuard>
            <OtaMappings />
          </AuthGuard>
        ),
      },
      {
        path: 'guest/login',
        element: <GuestLogin />,
      },
      {
        path: 'guest/signup',
        element: <GuestSignup />,
      },
      {
        path: 'guest',
        element: (
          <AuthGuard>
            <GuestDashboard />
          </AuthGuard>
        ),
      },
      {
        path: 'guest/bookings',
        element: (
          <AuthGuard>
            <MyBookings />
          </AuthGuard>
        ),
      },
      {
        path: 'guest/profile',
        element: (
          <AuthGuard>
            <GuestProfile />
          </AuthGuard>
        ),
      },
      {
        path: 'messages',
        element: (
          <AuthGuard>
            <MessageGuest />
          </AuthGuard>
        ),
      },
      {
        path: 'bookings/manual',
        element: (
          <RoleGuard allowedRoles={['Admin', 'Manager', 'Owner', 'Partner']}>
            <ManualBookingForm />
          </RoleGuard>
        ),
      },
      {
        path: 'bookings/:id',
        element: (
          <AuthGuard>
            <BookingDetail />
          </AuthGuard>
        ),
      },
      {
        path: 'bookings/:id/edit',
        element: (
          <AuthGuard>
            <BookingEdit />
          </AuthGuard>
        ),
      },
      {
        path: 'book',
        element: <Landing />,
      },
      {
        path: 'book/search',
        element: <SearchResults />,
      },
      {
        path: 'book/flow',
        element: <BookingFlow />,
      },
      {
        path: 'book/confirm',
        element: <BookingConfirmation />,
      },
      {
        path: 'owner',
        element: (
          <AuthGuard>
            <OwnerDashboard />
          </AuthGuard>
        ),
      },
      {
        path: 'admin',
        element: (
          <RoleGuard allowedRoles={['Admin']}>
            <AdminPanel />
          </RoleGuard>
        ),
      },
      {
        path: 'admin/*',
        element: (
          <RoleGuard allowedRoles={['Admin']}>
            <AdminPanel />
          </RoleGuard>
        ),
      },
      {
        path: '*',
        element: (
          <div className="text-gray-700 dark:text-gray-200">
            <h2 className="text-xl font-bold">404</h2>
            <p className="mt-2">Page not found.</p>
          </div>
        ),
      },
    ],
  },
]

export const router = createBrowserRouter(routes)
