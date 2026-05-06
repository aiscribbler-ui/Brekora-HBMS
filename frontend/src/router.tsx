import { createBrowserRouter, type RouteObject } from 'react-router-dom'
import App from '@/App'
import { AuthGuard } from '@/components/auth/AuthGuard'
import { RoleGuard } from '@/components/auth/RoleGuard'
import SetupRedirect from '@/components/auth/SetupRedirect'
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

export const routes: RouteObject[] = [
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <SetupRedirect /> },
      {
        path: 'dashboard',
        element: (
          <AuthGuard>
            <ManagerDashboard />
          </AuthGuard>
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
          <RoleGuard allowedRoles={['Admin', 'Manager', 'Owner']}>
            <TwoFactorEnrol />
          </RoleGuard>
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
