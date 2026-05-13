import type { PnLSummary as PnLSummaryType } from '@/services/ownerApi'

const inr = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' })

interface Props {
  data: PnLSummaryType
}

export default function PnLSummary({ data }: Props) {
  const items = [
    { label: 'Gross Revenue', value: data.gross_revenue },
    { label: 'OTA Commission', value: data.ota_commission },
    { label: 'Partner Commission', value: data.partner_commission },
    { label: 'GST', value: data.gst },
    { label: 'Net Distributable', value: data.net_distributable },
  ]

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
      {items.map((item) => (
        <div
          key={item.label}
          className="rounded-xl bg-white p-4 shadow-sm border border-gray-200 dark:border-gray-700 dark:bg-gray-800"
        >
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
            {item.label}
          </p>
          <p className="mt-1 text-xl font-bold text-gray-900 dark:text-gray-100">
            {inr.format(item.value)}
          </p>
        </div>
      ))}
    </div>
  )
}
