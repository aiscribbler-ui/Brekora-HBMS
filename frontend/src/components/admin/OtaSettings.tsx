import { useEffect, useState } from 'react'
import {
  fetchGmailStatus,
  initiateGmailAuth,
  fetchOtaSettings,
  updateOtaSettings,
  type OtaSettings as OtaSettingsType,
  type GmailStatus,
} from '@/services/adminApi'

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
  const [gmail, setGmail] = useState<GmailStatus | null>(null)
  const [gmailLoading, setGmailLoading] = useState(false)

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

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const data = await fetchGmailStatus()
        if (!cancelled) setGmail(data)
      } catch {
        if (!cancelled) setGmail({ connected: false, status: 'error' })
      }
    }
    load()
    const id = setInterval(load, 10000)
    return () => {
      cancelled = true
      clearInterval(id)
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

  const connectGmail = async () => {
    setGmailLoading(true)
    try {
      const { auth_url } = await initiateGmailAuth()
      window.open(auth_url, '_blank')
    } catch {
      setToast({ message: 'Failed to start Gmail OAuth', type: 'error' })
      setTimeout(() => setToast(null), 4000)
    } finally {
      setGmailLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">OTA Settings</h2>

      {toast && (
        <div
          className={`rounded-md p-3 text-sm font-medium ${
            toast.type === 'success' ? 'bg-success-light text-success-dark' : 'bg-red-50 dark:bg-red-900/20 text-red-800 dark:text-red-400'
          }`}
        >
          {toast.message}
        </div>
      )}

      <div className="max-w-lg space-y-4">
        {toggles.map(({ key, label }) => (
          <div key={key} className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{label}</span>
            <button
              type="button"
              aria-label={label}
              aria-pressed={!!settings[key]}
              onClick={() => toggle(key)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 ${
                settings[key] ? 'bg-brand-600' : 'bg-gray-200 dark:bg-gray-600'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white dark:bg-gray-100 transition-transform ${
                  settings[key] ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
        ))}

        <div>
          <label htmlFor="confidenceThreshold" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
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
          <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
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

        <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
            Gmail Connection
          </h3>
          <div className="mt-2 flex items-center justify-between">
            <div className="text-sm text-gray-600 dark:text-gray-400">
              {gmail?.connected ? (
                <span className="flex items-center gap-2">
                  <span className="inline-block h-2 w-2 rounded-full bg-green-500" />
                  Connected {gmail.email ? `(${gmail.email})` : ''}
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <span className="inline-block h-2 w-2 rounded-full bg-red-500" />
                  Not connected
                </span>
              )}
            </div>
            {!gmail?.connected && (
              <button
                type="button"
                onClick={connectGmail}
                disabled={gmailLoading}
                className="inline-flex justify-center rounded-md border border-transparent bg-brand-600 px-3 py-1.5 text-sm font-medium text-white shadow-sm hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 disabled:opacity-50"
              >
                {gmailLoading ? 'Opening...' : 'Connect Gmail'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
