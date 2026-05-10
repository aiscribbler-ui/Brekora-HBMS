import { useState, useEffect, useCallback } from 'react'
import { api } from '@/lib/api'
import {
  ChatBubbleLeftRightIcon,
  PhoneIcon,
  EnvelopeIcon,
  DocumentDuplicateIcon,
} from '@heroicons/react/24/outline'

interface BookingStub {
  id: string
  check_in: string
  check_out: string
  status: string
  guest_name?: string
  guest_phone?: string
  guest_email?: string
}

const TEMPLATES = [
  {
    id: 'welcome',
    label: 'Welcome',
    text: 'Hi {{name}}, welcome to {{property}}! Your booking ({{ref}}) is confirmed for {{check_in}} to {{check_out}}. We look forward to hosting you.',
  },
  {
    id: 'checkin',
    label: 'Check-in Instructions',
    text: 'Hi {{name}}, your check-in is on {{check_in}}. Property address: {{address}}. Contact us at {{phone}} if you need assistance.',
  },
  {
    id: 'payment',
    label: 'Payment Reminder',
    text: 'Hi {{name}}, this is a friendly reminder to complete payment for your booking {{ref}} due by {{due_date}}. Pay here: {{link}}',
  },
  {
    id: 'feedback',
    label: 'Feedback Request',
    text: 'Hi {{name}}, thank you for staying with us! We would love your feedback. Please reply to this message or email us at {{email}}.',
  },
  {
    id: 'custom',
    label: 'Custom',
    text: '',
  },
]

export default function MessageGuest() {
  const [bookings, setBookings] = useState<BookingStub[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [selectedBookingId, setSelectedBookingId] = useState<string>('')
  const [recipientName, setRecipientName] = useState('')
  const [recipientPhone, setRecipientPhone] = useState('')
  const [recipientEmail, setRecipientEmail] = useState('')
  const [selectedTemplate, setSelectedTemplate] = useState('custom')
  const [message, setMessage] = useState('')
  const [copied, setCopied] = useState(false)

  const loadBookings = useCallback(async () => {
    setIsLoading(true)
    try {
      const { data } = await api.get<BookingStub[]>('/bookings')
      // Enrich with guest details if available (line_items may hold guest info)
      const enriched = data.map((b) => {
        const li = Array.isArray((b as unknown as Record<string, unknown>).line_items)
          ? ((b as unknown as Record<string, unknown>).line_items as Array<Record<string, unknown>>)
          : []
        const guest = li.find((item) => item?.item_type === 'guest_details') || (li[0] as Record<string, unknown> | undefined)
        return {
          ...b,
          guest_name:
            (guest?.guest_name as string) ||
            (guest?.name as string) ||
            'Guest',
          guest_phone:
            (guest?.guest_phone as string) ||
            (guest?.phone as string) ||
            '',
          guest_email:
            (guest?.guest_email as string) ||
            (guest?.email as string) ||
            '',
        }
      })
      setBookings(enriched)
    } catch {
      setError('Failed to load bookings.')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    loadBookings()
  }, [loadBookings])

  useEffect(() => {
    const template = TEMPLATES.find((t) => t.id === selectedTemplate)
    if (template && template.id !== 'custom') {
      setMessage(template.text)
    }
  }, [selectedTemplate])

  const handleSelectBooking = (bookingId: string) => {
    setSelectedBookingId(bookingId)
    const b = bookings.find((x) => x.id === bookingId)
    if (b) {
      setRecipientName(b.guest_name || '')
      setRecipientPhone(b.guest_phone || '')
      setRecipientEmail(b.guest_email || '')
    }
  }

  const replaceVariables = (text: string): string => {
    const b = bookings.find((x) => x.id === selectedBookingId)
    return text
      .replace(/\{\{name\}\}/g, recipientName || 'Guest')
      .replace(/\{\{ref\}\}/g, selectedBookingId ? `BKK-${selectedBookingId.slice(0, 6).toUpperCase()}` : 'BKK-XXXXXX')
      .replace(/\{\{check_in\}\}/g, b?.check_in || '___')
      .replace(/\{\{check_out\}\}/g, b?.check_out || '___')
      .replace(/\{\{property\}\}/g, 'our property')
      .replace(/\{\{address\}\}/g, 'property address')
      .replace(/\{\{phone\}\}/g, 'reception phone')
      .replace(/\{\{email\}\}/g, 'support@brekora.com')
      .replace(/\{\{due_date\}\}/g, b?.check_in || '___')
      .replace(/\{\{link\}\}/g, 'https://brekora.com/pay')
  }

  const finalMessage = replaceVariables(message)

  const whatsappUrl =
    recipientPhone
      ? `https://wa.me/${recipientPhone.replace(/\D/g, '')}?text=${encodeURIComponent(finalMessage)}`
      : ''

  const mailtoUrl =
    recipientEmail
      ? `mailto:${recipientEmail}?subject=${encodeURIComponent('Message from Brekora')}&body=${encodeURIComponent(finalMessage)}`
      : ''

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(finalMessage)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // ignore
    }
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center gap-2">
        <ChatBubbleLeftRightIcon className="h-6 w-6 text-brand-600" />
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Message Guest</h1>
      </div>

      {error && (
        <div className="p-4 bg-red-50 text-red-700 rounded-xl border border-red-200" role="alert">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column — bookings list */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 lg:col-span-1">
          <h2 className="text-sm font-semibold text-gray-900 mb-3">Recent Bookings</h2>
          {isLoading ? (
            <div className="space-y-3 animate-pulse">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-14 bg-gray-200 rounded-xl" />
              ))}
            </div>
          ) : bookings.length === 0 ? (
            <p className="text-sm text-gray-500">No bookings found.</p>
          ) : (
            <ul className="space-y-2 max-h-96 overflow-y-auto pr-1">
              {bookings.slice(0, 20).map((b) => (
                <li key={b.id}>
                  <button
                    onClick={() => handleSelectBooking(b.id)}
                    className={`w-full text-left p-3 rounded-xl border transition-colors ${
                      selectedBookingId === b.id
                        ? 'border-brand-300 bg-brand-50'
                        : 'border-gray-100 hover:bg-gray-50'
                    }`}
                  >
                    <p className="text-sm font-medium text-gray-900">{b.guest_name || 'Guest'}</p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {b.check_in} → {b.check_out}
                    </p>
                    {b.guest_phone && (
                      <p className="text-xs text-gray-400 mt-0.5">{b.guest_phone}</p>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Right column — composer */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 lg:col-span-2 space-y-4">
          <h3 className="text-sm font-semibold text-gray-900 mb-1">Compose Message</h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Guest Name</label>
              <input
                type="text"
                value={recipientName}
                onChange={(e) => setRecipientName(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                placeholder="e.g., Rahul Sharma"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Phone (with country code)</label>
              <input
                type="tel"
                value={recipientPhone}
                onChange={(e) => setRecipientPhone(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                placeholder="e.g., 919876543210"
              />
            </div>
            <div className="sm:col-span-2">
              <label className="block text-xs font-medium text-gray-700 mb-1">Email</label>
              <input
                type="email"
                value={recipientEmail}
                onChange={(e) => setRecipientEmail(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                placeholder="guest@example.com"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Template</label>
            <div className="flex flex-wrap gap-2">
              {TEMPLATES.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => setSelectedTemplate(t.id)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                    selectedTemplate === t.id
                      ? 'bg-brand-600 text-white border-brand-600'
                      : 'bg-white text-gray-700 border-gray-200 hover:bg-gray-50'
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Message</label>
            <textarea
              rows={6}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              placeholder="Type your message here..."
            />
            <p className="text-xs text-gray-400 mt-1">
              Variables: {'{{name}}, {{ref}}, {{check_in}}, {{check_out}}, {{property}}, {{address}}, {{phone}}, {{email}}, {{due_date}}, {{link}}'}
            </p>
          </div>

          {/* Preview */}
          <div className="bg-gray-50 rounded-xl p-4 border border-gray-100">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Preview</p>
            <p className="text-sm text-gray-800 whitespace-pre-wrap">{finalMessage}</p>
          </div>

          {/* Actions */}
          <div className="flex flex-wrap gap-3">
            <button
              onClick={handleCopy}
              className="inline-flex items-center gap-2 px-4 py-2 bg-white text-gray-700 border border-gray-300 text-sm font-medium rounded-lg hover:bg-gray-50 transition-colors"
            >
              <DocumentDuplicateIcon className="h-4 w-4" />
              {copied ? 'Copied!' : 'Copy Text'}
            </button>

            {recipientEmail && (
              <a
                href={mailtoUrl}
                className="inline-flex items-center gap-2 px-4 py-2 bg-white text-gray-700 border border-gray-300 text-sm font-medium rounded-lg hover:bg-gray-50 transition-colors"
              >
                <EnvelopeIcon className="h-4 w-4" />
                Open Email
              </a>
            )}

            {recipientPhone && (
              <a
                href={whatsappUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white text-sm font-medium rounded-lg hover:bg-emerald-700 transition-colors shadow-sm"
              >
                <PhoneIcon className="h-4 w-4" />
                Send via WhatsApp
              </a>
            )}

            {!recipientPhone && !recipientEmail && (
              <p className="text-xs text-gray-400">Enter a phone number or email to send</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
