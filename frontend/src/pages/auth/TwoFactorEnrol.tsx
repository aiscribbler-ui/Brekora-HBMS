import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Loader2, ShieldCheck, Smartphone } from 'lucide-react'
import { setupTwoFactor, verifyTwoFactorEnrol, disableTwoFactor, isAxiosError } from '@/services/authApi'

export default function TwoFactorEnrol() {
  const navigate = useNavigate()
  const [secret, setSecret] = useState<string>('')
  const [provisioningUri, setProvisioningUri] = useState<string>('')
  const [code, setCode] = useState('')
  const [disableCode, setDisableCode] = useState('')
  const [loading, setLoading] = useState(false)
  const [verifying, setVerifying] = useState(false)
  const [disabling, setDisabling] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const startSetup = async () => {
    setError(null)
    setSuccess(null)
    setLoading(true)
    try {
      const data = await setupTwoFactor()
      setSecret(data.secret)
      setProvisioningUri(data.provisioning_uri)
    } catch (err) {
      if (isAxiosError<{ detail?: string }>(err)) {
        setError(err.response?.data?.detail || 'Failed to start 2FA setup.')
      } else {
        setError('Failed to start 2FA setup.')
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    startSetup()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const verify = async () => {
    if (!secret || code.length !== 6) return
    setError(null)
    setSuccess(null)
    setVerifying(true)
    try {
      await verifyTwoFactorEnrol(secret, code)
      setSuccess('2FA enabled successfully. You will be asked for a code on next sign-in.')
      setCode('')
    } catch (err) {
      if (isAxiosError<{ detail?: string }>(err)) {
        setError(err.response?.data?.detail || 'Invalid code. Please try again.')
      } else {
        setError('Invalid code. Please try again.')
      }
    } finally {
      setVerifying(false)
    }
  }

  const disable = async () => {
    if (disableCode.length !== 6) return
    setError(null)
    setSuccess(null)
    setDisabling(true)
    try {
      await disableTwoFactor(disableCode)
      setSuccess('2FA disabled. We recommend re-enabling it for your account safety.')
      setDisableCode('')
      // refresh secret/QR for re-setup
      await startSetup()
    } catch (err) {
      if (isAxiosError<{ detail?: string }>(err)) {
        setError(err.response?.data?.detail || 'Could not disable 2FA.')
      } else {
        setError('Could not disable 2FA.')
      }
    } finally {
      setDisabling(false)
    }
  }

  const qrSrc = provisioningUri
    ? `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(provisioningUri)}`
    : null

  return (
    <div className="max-w-3xl mx-auto py-8 px-4">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 text-white flex items-center justify-center">
          <ShieldCheck className="w-5 h-5" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Two-Factor Authentication</h1>
          <p className="text-sm text-gray-500">Add an extra layer of security to your account.</p>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg border border-red-200" role="alert">
          {error}
        </div>
      )}
      {success && (
        <div className="mb-4 p-3 bg-success-light text-success-dark rounded-lg border border-success" role="status">
          {success}
        </div>
      )}

      <section className="bg-white rounded-xl border border-gray-100 shadow-sm p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-2 flex items-center gap-2">
          <Smartphone className="w-5 h-5 text-brand-600" />
          Step 1 — Scan with your authenticator
        </h2>
        <p className="text-sm text-gray-500 mb-4">
          Use Google Authenticator, 1Password, Authy, or any compatible app to scan the QR code below.
        </p>
        {loading ? (
          <div className="flex items-center gap-2 text-gray-500 text-sm">
            <Loader2 className="w-4 h-4 animate-spin" />
            Generating secret…
          </div>
        ) : qrSrc ? (
          <div className="flex flex-col md:flex-row gap-6 items-start">
            <img src={qrSrc} alt="2FA QR code" className="rounded-lg border border-gray-200 bg-white p-2" width={200} height={200} />
            <div className="flex-1">
              <p className="text-xs text-gray-500 mb-1">Or enter this secret manually:</p>
              <code className="block break-all bg-gray-50 border border-gray-200 rounded-md px-2.5 py-2 text-sm font-mono text-gray-800">
                {secret}
              </code>
            </div>
          </div>
        ) : null}
      </section>

      <section className="bg-white rounded-xl border border-gray-100 shadow-sm p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-2">
          Step 2 — Enter the 6-digit code
        </h2>
        <p className="text-sm text-gray-500 mb-4">
          Confirm the setup by entering the current code from your authenticator app.
        </p>
        <div className="flex gap-3 items-end">
          <div className="flex-1 max-w-xs">
            <label htmlFor="enrol-code" className="block text-xs font-medium text-gray-500 mb-1">
              Code
            </label>
            <input
              id="enrol-code"
              type="text"
              inputMode="numeric"
              maxLength={6}
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
              placeholder="000000"
              className="block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm text-center tracking-widest font-mono focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </div>
          <button
            type="button"
            onClick={verify}
            disabled={verifying || code.length !== 6 || !secret}
            className="py-2 px-4 bg-brand-600 text-white font-medium rounded-md hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center gap-2"
          >
            {verifying ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
            Enable 2FA
          </button>
        </div>
      </section>

      <section className="bg-white rounded-xl border border-gray-100 shadow-sm p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-2">Already enrolled? Disable 2FA</h2>
        <p className="text-sm text-gray-500 mb-4">
          Enter a current code to remove 2FA from your account.
        </p>
        <div className="flex gap-3 items-end">
          <div className="flex-1 max-w-xs">
            <label htmlFor="disable-code" className="block text-xs font-medium text-gray-500 mb-1">
              Code
            </label>
            <input
              id="disable-code"
              type="text"
              inputMode="numeric"
              maxLength={6}
              value={disableCode}
              onChange={(e) => setDisableCode(e.target.value.replace(/\D/g, ''))}
              placeholder="000000"
              className="block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm text-center tracking-widest font-mono focus:border-red-500 focus:outline-none focus:ring-1 focus:ring-red-500"
            />
          </div>
          <button
            type="button"
            onClick={disable}
            disabled={disabling || disableCode.length !== 6}
            className="py-2 px-4 bg-white text-red-700 font-medium rounded-md border border-red-200 hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center gap-2"
          >
            {disabling ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
            Disable
          </button>
        </div>
      </section>

      <div className="mt-6 text-center">
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="text-sm text-gray-600 hover:text-gray-900 underline"
        >
          ← Back
        </button>
      </div>
    </div>
  )
}
