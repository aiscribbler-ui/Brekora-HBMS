import { useEffect, useRef, useState } from 'react'

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string
            callback: (response: { credential: string }) => void
            ux_mode?: 'popup' | 'redirect'
            auto_select?: boolean
          }) => void
          renderButton: (
            parent: HTMLElement,
            options: {
              type?: 'standard' | 'icon'
              theme?: 'outline' | 'filled_blue' | 'filled_black'
              size?: 'small' | 'medium' | 'large'
              shape?: 'rectangular' | 'pill' | 'circle' | 'square'
              text?: 'signin_with' | 'signup_with' | 'continue_with' | 'signin'
              width?: number | string
            },
          ) => void
        }
      }
    }
  }
}

const GIS_SCRIPT_URL = 'https://accounts.google.com/gsi/client'

interface Props {
  onIdToken: (idToken: string) => Promise<void> | void
  onError?: (message: string) => void
  width?: number
}

export default function GoogleSignInButton({ onIdToken, onError, width = 320 }: Props) {
  const ref = useRef<HTMLDivElement | null>(null)
  const [scriptLoaded, setScriptLoaded] = useState(false)
  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined

  useEffect(() => {
    if (!clientId) return
    if (window.google?.accounts?.id) {
      setScriptLoaded(true)
      return
    }
    const existing = document.querySelector<HTMLScriptElement>(`script[src="${GIS_SCRIPT_URL}"]`)
    if (existing) {
      existing.addEventListener('load', () => setScriptLoaded(true))
      return
    }
    const script = document.createElement('script')
    script.src = GIS_SCRIPT_URL
    script.async = true
    script.defer = true
    script.onload = () => setScriptLoaded(true)
    script.onerror = () => onError?.('Could not load Google Sign-In.')
    document.head.appendChild(script)
  }, [clientId, onError])

  useEffect(() => {
    if (!scriptLoaded || !clientId || !ref.current || !window.google) return
    window.google.accounts.id.initialize({
      client_id: clientId,
      ux_mode: 'popup',
      callback: async ({ credential }) => {
        try {
          await onIdToken(credential)
        } catch (err) {
          const message = err instanceof Error ? err.message : 'Google sign-in failed.'
          onError?.(message)
        }
      },
    })
    window.google.accounts.id.renderButton(ref.current, {
      type: 'standard',
      theme: 'outline',
      size: 'large',
      shape: 'rectangular',
      text: 'signin_with',
      width,
    })
  }, [scriptLoaded, clientId, onIdToken, onError, width])

  if (!clientId) {
    return (
      <button
        type="button"
        disabled
        className="w-full py-2.5 px-4 bg-white text-gray-500 font-medium rounded-lg border border-gray-300 cursor-not-allowed flex items-center justify-center gap-2"
        title="VITE_GOOGLE_CLIENT_ID is not configured"
      >
        Sign in with Google (not configured)
      </button>
    )
  }

  return <div ref={ref} className="flex justify-center" />
}
