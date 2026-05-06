import { createBrowserRouter, Navigate, type RouteObject } from 'react-router-dom'
import App from '@/App'
import RequireRole from '@/components/auth/RequireRole'
import Login from '@/pages/auth/Login'
import TwoFactor from '@/pages/auth/TwoFactor'
import TwoFactorEnrol from '@/pages/auth/TwoFactorEnrol'
import ManagerDashboard from '@/pages/dashboard/ManagerDashboard'
import GuestLogin from '@/pages/guest/GuestLogin'
import GuestSignup from '@/pages/guest/GuestSignup'
import GuestDashboard from '@/pages/guest/GuestDashboard'
import PropertyList from '@/pages/properties/PropertyList'
import PropertyDetail from '@/pages/properties/PropertyDetail'
import RoomTypeList from '@/pages/properties/RoomTypeList'
import RoomTypeForm from '@/pages/properties/RoomTypeForm'
import CalendarGrid from '@/pages/calendar/CalendarGrid'
import PackageList from '@/pages/packages/PackageList'
import PackageBuilder from '@/pages/packages/PackageBuilder'
import OtaQueue from '@/pages/ota/OtaQueue'
import ManualBookingForm from '@/pages/bookings/ManualBookingForm'
import BookingDetail from '@/pages/bookings/BookingDetail'
import BookingEdit from '@/pages/bookings/BookingEdit'
import Landing from '@/pages/public/Landing'
import SearchResults from '@/pages/public/SearchResults'
import BookingFlow from '@/pages/public/BookingFlow'
import BookingConfirmation from '@/pages/public/BookingConfirmation'
import AdminPanel from '@/pages/admin/AdminPanel'
import OwnerDashboard from '@/pages/owner/OwnerDashboard'

const STAFF = ['Manager', 'Admin'] as const
const STAFF_OR_OWNER = ['Manager', 'Admin', 'Owner'] as const

export const routes: RouteObject[] = [
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      {
        path: 'dashboard',
        element: (
          <RequireRole allowed={STAFF_OR_OWNER}>
            <ManagerDashboard />
          </RequireRole>
        ),
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
          <RequireRole allowed={STAFF}>
            <PropertyList />
          </RequireRole>
        ),
      },
      {
        path: 'properties/:id',
        element: (
          <RequireRole allowed={STAFF}>
            <PropertyDetail />
          </RequireRole>
        ),
      },
      {
        path: 'properties/:id/room-types',
        element: (
          <RequireRole allowed={STAFF}>
            <RoomTypeList />
          </RequireRole>
        ),
      },
      {
        path: 'properties/:id/room-types/:roomTypeId',
        element: (
          <RequireRole allowed={STAFF}>
            <RoomTypeForm />
          </RequireRole>
        ),
      },
      {
        path: 'calendar',
        element: (
          <RequireRole allowed={STAFF}>
            <CalendarGrid />
          </RequireRole>
        ),
      },
      {
        path: 'packages',
        element: (
          <RequireRole allowed={STAFF}>
            <PackageList />
          </RequireRole>
        ),
      },
      {
        path: 'packages/:id',
        element: (
          <RequireRole allowed={STAFF}>
            <PackageBuilder />
          </RequireRole>
        ),
      },
      {
        path: 'ota/queue',
        element: (
          <RequireRole allowed={STAFF}>
            <OtaQueue />
          </RequireRole>
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
          <RequireRole allowed={['Guest']} redirectTo="/guest/login">
            <GuestDashboard />
          </RequireRole>
        ),
      },
      {
        path: 'bookings/manual',
        element: (
          <RequireRole allowed={STAFF}>
            <ManualBookingForm />
          </RequireRole>
        ),
      },
      {
        path: 'bookings/:id',
        element: (
          <RequireRole allowed={STAFF}>
            <BookingDetail />
          </RequireRole>
        ),
      },
      {
        path: 'bookings/:id/edit',
        element: (
          <RequireRole allowed={STAFF}>
            <BookingEdit />
          </RequireRole>
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
          <RequireRole allowed={['Owner', 'Admin']}>
            <OwnerDashboard />
          </RequireRole>
        ),
      },
      {
        path: 'admin',
        element: (
          <RequireRole allowed={['Admin']}>
            <AdminPanel />
          </RequireRole>
        ),
      },
      {
        path: 'admin/*',
        element: (
          <RequireRole allowed={['Admin']}>
            <AdminPanel />
          </RequireRole>
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
