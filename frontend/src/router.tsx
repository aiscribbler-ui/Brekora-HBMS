import { createBrowserRouter, Navigate, type RouteObject } from 'react-router-dom'
import App from '@/App'
import Login from '@/pages/auth/Login'
import TwoFactor from '@/pages/auth/TwoFactor'
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

export const routes: RouteObject[] = [
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      {
        path: 'dashboard',
        element: <ManagerDashboard />,
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
        path: 'properties',
        element: <PropertyList />,
      },
      {
        path: 'properties/:id',
        element: <PropertyDetail />,
      },
      {
        path: 'properties/:id/room-types',
        element: <RoomTypeList />,
      },
      {
        path: 'properties/:id/room-types/:roomTypeId',
        element: <RoomTypeForm />,
      },
      {
        path: 'calendar',
        element: <CalendarGrid />,
      },
      {
        path: 'packages',
        element: <PackageList />,
      },
      {
        path: 'packages/:id',
        element: <PackageBuilder />,
      },
      {
        path: 'ota/queue',
        element: <OtaQueue />,
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
        element: <GuestDashboard />,
      },
      {
        path: 'bookings/manual',
        element: <ManualBookingForm />,
      },
      {
        path: 'bookings/:id',
        element: <BookingDetail />,
      },
      {
        path: 'bookings/:id/edit',
        element: <BookingEdit />,
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
        path: 'admin',
        element: <AdminPanel />,
      },
      {
        path: 'admin/*',
        element: <AdminPanel />,
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
