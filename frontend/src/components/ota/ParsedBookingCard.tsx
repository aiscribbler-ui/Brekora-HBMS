import {
  EnvelopeOpenIcon,
  CheckCircleIcon,
  PencilSquareIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  UserIcon,
  CalendarIcon,
  PhoneIcon,
  UsersIcon,
  HomeIcon,
  HashtagIcon,
} from '@heroicons/react/24/outline'
import type { ParsedBooking } from '@/services/otaApi'

interface ParsedBookingCardProps {
  booking: ParsedBooking
  onConfirm: () => void
  onEdit: () => void
  onReject: () => void
  rawEmailUrl?: string | null
}

function confidenceColor(score: number): string {
  if (score >= 0.95) return 'text-success bg-success-light border-success'
  if (score >= 0.8) return 'text-secondary bg-secondary-light border-secondary'
  return 'text-error bg-error-light border-error'
}

function confidenceLabel(score: number): string {
  if (score >= 0.95) return 'High'
  if (score >= 0.8) return 'Medium'
  return 'Low'
}

function sourceBadge(source: string) {
  const styles: Record<string, string> = {
    airbnb: 'bg-rose-100 dark:bg-rose-900/20 text-rose-800 dark:text-rose-400',
    mmt: 'bg-blue-100 dark:bg-blue-900/20 text-blue-800 dark:text-blue-400',
    goibibo: 'bg-orange-100 dark:bg-orange-900/20 text-orange-800 dark:text-orange-400',
    other: 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300',
  }
  const labels: Record<string, string> = {
    airbnb: 'Airbnb',
    mmt: 'MakeMyTrip',
    goibibo: 'Goibibo',
    other: 'Other',
  }
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${styles[source] || styles.other}`}>
      {labels[source] || source}
    </span>
  )
}

function statusBadge(status: string) {
  const styles: Record<string, string> = {
    pending: 'bg-warning-light text-warning-dark',
    confirmed: 'bg-success-light text-success-dark',
    rejected: 'bg-error-light text-error-dark',
    edited: 'bg-info-light text-info-dark',
  }
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium capitalize ${styles[status] || 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300'}`}>
      {status}
    </span>
  )
}

export default function ParsedBookingCard({
  booking,
  onConfirm,
  onEdit,
  onReject,
  rawEmailUrl,
}: ParsedBookingCardProps) {
  const canAct = booking.status === 'pending' || booking.status === 'edited'

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm">
      <div className="p-4 sm:p-6 space-y-4">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div className="flex items-center gap-2">
            {sourceBadge(booking.source_type)}
            {statusBadge(booking.status)}
          </div>
          <div
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded border text-sm font-medium ${confidenceColor(booking.confidence_score)}`}
            title={`Confidence: ${(booking.confidence_score * 100).toFixed(1)}%`}
          >
            {booking.confidence_score < 0.8 && (
              <ExclamationTriangleIcon className="h-4 w-4" />
            )}
            <span>{(booking.confidence_score * 100).toFixed(0)}%</span>
            <span className="text-xs opacity-75">({confidenceLabel(booking.confidence_score)})</span>
          </div>
        </div>

        {/* Parsed fields */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="flex items-start gap-2">
            <UserIcon className="h-4 w-4 text-gray-400 dark:text-gray-500 mt-0.5 shrink-0" />
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">Guest Name</p>
              <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{booking.guest_name || '—'}</p>
            </div>
          </div>

          <div className="flex items-start gap-2">
            <EnvelopeOpenIcon className="h-4 w-4 text-gray-400 dark:text-gray-500 mt-0.5 shrink-0" />
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">Email</p>
              <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{booking.guest_email || '—'}</p>
            </div>
          </div>

          <div className="flex items-start gap-2">
            <PhoneIcon className="h-4 w-4 text-gray-400 dark:text-gray-500 mt-0.5 shrink-0" />
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">Phone</p>
              <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{booking.guest_phone || '—'}</p>
            </div>
          </div>

          <div className="flex items-start gap-2">
            <UsersIcon className="h-4 w-4 text-gray-400 dark:text-gray-500 mt-0.5 shrink-0" />
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">Guests</p>
              <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{booking.num_guests ?? '—'}</p>
            </div>
          </div>

          <div className="flex items-start gap-2">
            <CalendarIcon className="h-4 w-4 text-gray-400 dark:text-gray-500 mt-0.5 shrink-0" />
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">Dates</p>
              <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                {booking.check_in && booking.check_out
                  ? `${booking.check_in} → ${booking.check_out}`
                  : '—'}
              </p>
            </div>
          </div>

          <div className="flex items-start gap-2">
            <HomeIcon className="h-4 w-4 text-gray-400 dark:text-gray-500 mt-0.5 shrink-0" />
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">Room Type</p>
              <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{booking.room_type || '—'}</p>
            </div>
          </div>

          <div className="flex items-start gap-2">
            <HashtagIcon className="h-4 w-4 text-gray-400 dark:text-gray-500 mt-0.5 shrink-0" />
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">OTA Reference</p>
              <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{booking.ota_reference || '—'}</p>
            </div>
          </div>
        </div>

        {/* Original email link */}
        {rawEmailUrl && (
          <div className="pt-2 border-t border-gray-100 dark:border-gray-700">
            <a
              href={rawEmailUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-sm text-brand-600 dark:text-brand-400 hover:text-brand-700 dark:hover:text-brand-300 hover:underline"
            >
              <EnvelopeOpenIcon className="h-4 w-4" />
              View original email
            </a>
          </div>
        )}

        {/* Actions */}
        {canAct && (
          <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-gray-100 dark:border-gray-700">
            <button
              onClick={onConfirm}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md bg-success text-white hover:bg-success-dark transition-colors focus:outline-none focus:ring-2 focus:ring-success focus:ring-offset-2"
              aria-label={`Confirm booking for ${booking.guest_name || 'unknown guest'}`}
            >
              <CheckCircleIcon className="h-4 w-4" />
              Confirm
            </button>
            <button
              onClick={onEdit}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
              aria-label={`Edit booking for ${booking.guest_name || 'unknown guest'}`}
            >
              <PencilSquareIcon className="h-4 w-4" />
              Edit
            </button>
            <button
              onClick={onReject}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md bg-red-50 text-red-700 border border-red-200 hover:bg-red-100 transition-colors focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
              aria-label={`Reject booking for ${booking.guest_name || 'unknown guest'}`}
            >
              <XCircleIcon className="h-4 w-4" />
              Reject
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
