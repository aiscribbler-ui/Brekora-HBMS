import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { fetchSystemConfig, updateSystemConfig } from '@/services/adminApi'

const schema = z.object({
  gstRate: z.coerce.number().min(0).max(100),
  partnerAttributionLookbackDays: z.coerce.number().int().min(0).max(365),
})

type FormData = z.infer<typeof schema>

export default function SystemSettings() {
  const [saving, setSaving] = useState(false)
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null)
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isDirty },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      gstRate: 12,
      partnerAttributionLookbackDays: 30,
    },
  })

  useEffect(() => {
    let cancelled = false
    fetchSystemConfig()
      .then((data) => {
        if (!cancelled) reset(data)
      })
      .catch(() => {
        // keep defaults
      })
    return () => {
      cancelled = true
    }
  }, [reset])

  const onSubmit = async (data: FormData) => {
    setSaving(true)
    try {
      await updateSystemConfig(data)
      setToast({ message: 'Settings saved successfully', type: 'success' })
      reset(data)
    } catch {
      setToast({ message: 'Failed to save settings', type: 'error' })
    } finally {
      setSaving(false)
      setTimeout(() => setToast(null), 4000)
    }
  }

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">System Settings</h2>

      {toast && (
        <div
          className={`rounded-md p-3 text-sm font-medium ${
            toast.type === 'success' ? 'bg-success-light text-success-dark' : 'bg-red-50 dark:bg-red-900/20 text-red-800 dark:text-red-400'
          }`}
        >
          {toast.message}
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="max-w-lg space-y-4">
        <div>
          <label htmlFor="gstRate" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            GST Rate (%)
          </label>
          <input
            id="gstRate"
            type="number"
            step="0.01"
            {...register('gstRate')}
            className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-2 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 sm:text-sm"
          />
          {errors.gstRate && <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.gstRate.message}</p>}
        </div>

        <div>
          <label
            htmlFor="partnerAttributionLookbackDays"
            className="block text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            Partner Attribution Lookback (days)
          </label>
          <input
            id="partnerAttributionLookbackDays"
            type="number"
            {...register('partnerAttributionLookbackDays')}
            className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-2 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 sm:text-sm"
          />
          {errors.partnerAttributionLookbackDays && (
            <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.partnerAttributionLookbackDays.message}</p>
          )}
        </div>

        <button
          type="submit"
          disabled={saving || !isDirty}
          className="inline-flex justify-center rounded-md border border-transparent bg-brand-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Save'}
        </button>
      </form>
    </div>
  )
}
