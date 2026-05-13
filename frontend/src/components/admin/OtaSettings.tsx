import { useEffect, useState } from 'react'
import { fetchOtaSettings, updateOtaSettings, type OtaSettings as OtaSettingsType } from '@/services/adminApi'

type ToggleKey = 'autoConfirmAirbnb' | 'autoConfirmMmt' | 'autoConfirmGoibibo'

const toggles: { key: ToggleKey; label: string }[] = [
  { key: 'autoConfirmAirbnb', label: 'Auto-confirm Airbnb' },
  { key: 'autoConfirmMmt', label: 'Auto-confirm MakeMyTrip' },
  { key: 'autoConfirmGoibibo', label: 'Auto-confirm Goibibo' },
]

export default function OtaSettings() {
  const [settings, setSettings] = useState<OtaSettingsType>({
    autoConfirmAirbnb: false,
    autoConfirmMmt: false,
    autoConfirmGoibibo: false,
    confidenceThreshold: 0.9,
  })
  const [saving, setSaving] = useState(false)
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null)

  useEffect(() => {
    let cancelled = false
    fetchOtaSettings()
      .then((data) => {
        if (!cancelled) setSettings(data)
      })
      .catch(() => {
        // keep defaults
      })
    return () => {
      cancelled = true
    }
  }, [])

  const toggle = (key: ToggleKey) => {
    setSettings((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  const save = async () => {
    setSaving(true)
    try {
      const saved = await updateOtaSettings(settings)
      setSettings(saved)
      setToast({ message: 'OTA settings saved', type: 'success' })
    } catch {
      setToast({ message: 'Failed to save OTA settings', type: 'error' })
    } finally {
      setSaving(false)
      setTimeout(() => setToast(null), 4000)
    }
  }

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold text-gray-900">OTA Settings</h2>

      {toast && (
        <div
          className={`rounded-md p-3 text-sm font-medium ${
            toast.type === 'success' ? 'bg-success-light text-success-dark' : 'bg-red-50 text-red-800'
          }`}
        >
          {toast.message}
        </div>
      )}

      <div className="max-w-lg space-y-4">
        {toggles.map(({ key, label }) => (
          <div key={key} className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700">{label}</span>
            <button
              type="button"
              aria-label={label}
              aria-pressed={!!settings[key]}
              onClick={() => toggle(key)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 ${
                settings[key] ? 'bg-brand-600' : 'bg-gray-200'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  settings[key] ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
        ))}

        <div>
          <label htmlFor="confidenceThreshold" className="block text-sm font-medium text-gray-700">
            Confidence Threshold: {settings.confidenceThreshold.toFixed(2)}
          </label>
          <input
            id="confidenceThreshold"
            type="range"
            min={0.8}
            max={1.0}
            step={0.01}
            value={settings.confidenceThreshold}
            onChange={(e) =>
              setSettings((prev) => ({
                ...prev,
                confidenceThreshold: parseFloat(e.target.value),
              }))
            }
            className="mt-2 w-full accent-brand-600"
          />
          <div className="flex justify-between text-xs text-gray-500">
            <span>0.80</span>
            <span>1.00</span>
          </div>
        </div>

        <button
          type="button"
          onClick={save}
          disabled={saving}
          className="inline-flex justify-center rounded-md border border-transparent bg-brand-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Save'}
        </button>
      </div>
    </div>
  )
}
