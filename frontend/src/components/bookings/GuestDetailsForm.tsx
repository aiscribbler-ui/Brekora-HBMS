import { useFormContext } from 'react-hook-form'
import type { ManualBookingFormData } from '@/pages/bookings/ManualBookingForm'

export default function GuestDetailsForm() {
  const {
    register,
    formState: { errors },
  } = useFormContext<ManualBookingFormData>()

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-900">Guest Details</h3>

      <div>
        <label htmlFor="guestName" className="block text-sm font-medium text-gray-700">
          Full Name
        </label>
        <input
          id="guestName"
          type="text"
          autoComplete="name"
          {...register('guestName')}
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
        />
        {errors.guestName && (
          <p className="mt-1 text-sm text-red-600">{errors.guestName.message}</p>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label htmlFor="guestEmail" className="block text-sm font-medium text-gray-700">
            Email
          </label>
          <input
            id="guestEmail"
            type="email"
            autoComplete="email"
            {...register('guestEmail')}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
          {errors.guestEmail && (
            <p className="mt-1 text-sm text-red-600">{errors.guestEmail.message}</p>
          )}
        </div>

        <div>
          <label htmlFor="guestPhone" className="block text-sm font-medium text-gray-700">
            Phone
          </label>
          <input
            id="guestPhone"
            type="tel"
            autoComplete="tel"
            {...register('guestPhone')}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
          {errors.guestPhone && (
            <p className="mt-1 text-sm text-red-600">{errors.guestPhone.message}</p>
          )}
        </div>
      </div>

      <div>
        <label htmlFor="guestIdNumber" className="block text-sm font-medium text-gray-700">
          ID Number (Aadhaar / Passport / DL)
        </label>
        <input
          id="guestIdNumber"
          type="text"
          {...register('guestIdNumber')}
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
        />
        {errors.guestIdNumber && (
          <p className="mt-1 text-sm text-red-600">{errors.guestIdNumber.message}</p>
        )}
      </div>
    </div>
  )
}
