import type { PayoutRecord } from '@/services/ownerApi'

const inr = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' })

interface Props {
  data: PayoutRecord
}

export default function PayoutHistory({ data }: Props) {
  const total = data.net_distributable || 0
  const owner = data.owner_share ?? (total * (data.owner_percentage ?? 0)) / 100
  const brekora = data.brekora_share ?? (total * (data.brekora_percentage ?? 0)) / 100
  const ownerPct = total > 0 ? Math.round((owner / total) * 100) : 0
  const brekoraPct = total > 0 ? 100 - ownerPct : 0

  return (
    <div className="rounded-xl bg-white p-4 shadow-sm border border-gray-200 dark:border-gray-700 dark:bg-gray-800">
      <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">Revenue Split</h3>

      <div className="w-full h-8 flex rounded overflow-hidden">
        <div
          className="bg-brand-600 h-full flex items-center justify-center text-xs text-white font-medium"
          style={{ width: `${ownerPct}%`, minWidth: ownerPct > 0 ? '2rem' : '0' }}
          aria-label={`Owner share ${ownerPct}%`}
          title={`Owner ${ownerPct}%`}
        >
          {ownerPct > 8 && `${ownerPct}%`}
        </div>
        <div
          className="bg-gray-400 h-full flex items-center justify-center text-xs text-white font-medium"
          style={{ width: `${brekoraPct}%`, minWidth: brekoraPct > 0 ? '2rem' : '0' }}
          aria-label={`Brekora share ${brekoraPct}%`}
          title={`Brekora ${brekoraPct}%`}
        >
          {brekoraPct > 8 && `${brekoraPct}%`}
        </div>
      </div>

      <div className="mt-4 space-y-1 text-sm text-gray-700 dark:text-gray-300">
        <p>
          <span className="inline-block w-3 h-3 rounded-full bg-brand-600 mr-2" />
          Owner ({data.owner_percentage ?? ownerPct}%): {inr.format(owner)}
        </p>
        <p>
          <span className="inline-block w-3 h-3 rounded-full bg-gray-400 mr-2" />
          Brekora ({data.brekora_percentage ?? brekoraPct}%): {inr.format(brekora)}
        </p>
      </div>
    </div>
  )
}
