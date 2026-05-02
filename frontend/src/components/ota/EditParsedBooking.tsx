import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { isAxiosError } from '@/lib/api'
import { editOtaQueueItem, confirmOtaQueueItem, type ParsedBooking } from '@/services/otaApi'

const editSchema = z.object({
  guest_name: z.string().min(1, 'Guest name is required').optional(),
  guest_email: z.string().email('Invalid email').optional().or(z.literal('')),
  guest_phone: z.string().optional(),
  check_in: z.string().optional(),
  check_out: z.string().optional(),
  num_guests: z.coerce.number().min(1).optional(),
})

type EditFormData = z.infer<typeof editSchema>

interface EditParsedBookingProps {
  booking: ParsedBooking
  onSaved: (updated: ParsedBooking) => void
  onCancel: () => void
  onError: (message: string) => void
}

export default function EditParsedBooking({ booking, onSaved, onCancel, onError }: EditParsedBookingProps) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<EditFormData>({
    resolver: zodResolver(editSchema),
    defaultValues: {
      guest_name: booking.guest_name || '',
      guest_email: booking.guest_email || '',
      guest_phone: booking.guest_phone || '',
      check_in: booking.check_in || '',
      check_out: booking.check_out || '',
      num_guests: booking.num_guests || undefined,
    },
  })

  useEffect(() => {
    reset({
      guest_name: booking.guest_name || '',
      guest_email: booking.guest_email || '',
      guest_phone: booking.guest_phone || '',
      check_in: booking.check_in || '',
      check_out: booking.check_out || '',
      num_guests: booking.num_guests || undefined,
    })
  }, [booking, reset])

  const onSubmit = async (form: EditFormData) => {
    try {
      const payload = {
        parsed_data: { ...booking.parsed_data, ...form },
        guest_name: form.guest_name || undefined,
        guest_email: form.guest_email || undefined,
        guest_phone: form.guest_phone || undefined,
        check_in: form.check_in || undefined,
        check_out: form.check_out || undefined,
        num_guests: form.num_guests ?? undefined,
      }
      const edited = await editOtaQueueItem(booking.id, payload)
      const confirmed = await confirmOtaQueueItem(edited.id, {})
      onSaved(confirmed)
    } catch (err) {
      if (isAxiosError(err) && err.response?.data?.detail) {
        onError(err.response.data.detail)
      } else {
        onError('Failed to save and confirm booking.')
      }
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="bg-white rounded-lg border border-gray-200 shadow-sm p-4 sm:p-6 space-y-4">
      <h3 className="text-lg font-semibold text-gray-900">Edit Parsed Booking</h3>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="sm:col-span-2">
          <label htmlFor="edit-guest-name" className="block text-sm font-medium text-gray-700">
            Guest Name
          </label>
          <input
            id="edit-guest-name"
            type="text"
            {...register('guest_name')}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
          {errors.guest_name && (
            <p className="mt-1 text-sm text-red-600">{errors.guest_name.message}</p>
          )}
        </div>

        <div>
          <label htmlFor="edit-email" className="block text-sm font-medium text-gray-700">
            Email
          </label>
          <input
            id="edit-email"
            type="email"
            {...register('guest_email')}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
          {errors.guest_email && (
            <p className="mt-1 text-sm text-red-600">{errors.guest_email.message}</p>
          )}
        </div>

        <div>
          <label htmlFor="edit-phone" className="block text-sm font-medium text-gray-700">
            Phone
          </label>
          <input
            id="edit-phone"
            type="tel"
            {...register('guest_phone')}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
        </div>

        <div>
          <label htmlFor="edit-check-in" className="block text-sm font-medium text-gray-700">
            Check-in
          </label>
          <input
            id="edit-check-in"
            type="date"
            {...register('check_in')}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
        </div>

        <div>
          <label htmlFor="edit-check-out" className="block text-sm font-medium text-gray-700">
            Check-out
          </label>
          <input
            id="edit-check-out"
            type="date"
            {...register('check_out')}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
        </div>

        <div>
          <label htmlFor="edit-num-guests" className="block text-sm font-medium text-gray-700">
            Number of Guests
          </label>
          <input
            id="edit-num-guests"
            type="number"
            min={1}
            {...register('num_guests')}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
          {errors.num_guests && (
            <p className="mt-1 text-sm text-red-600">{errors.num_guests.message}</p>
          )}
        </div>
      </div>

      <div className="flex items-center gap-3 pt-2">
        <button
          type="submit"
          disabled={isSubmitting}
          className="inline-flex items-center gap-2 px-4 py-2 bg-brand-600 text-white text-sm font-medium rounded-md hover:bg-brand-700 disabled:opacity-50 transition-colors"
        >
          {isSubmitting ? 'Saving...' : 'Save & Confirm'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          disabled={isSubmitting}
          className="inline-flex items-center gap-2 px-4 py-2 bg-white text-gray-700 border border-gray-300 text-sm font-medium rounded-md hover:bg-gray-50 disabled:opacity-50 transition-colors"
        >
          Cancel
        </button>
      </div>
    </form>
  )
}
