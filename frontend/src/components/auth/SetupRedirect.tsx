import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '@/lib/api'

export default function SetupRedirect() {
  const navigate = useNavigate()
  const [checked, setChecked] = useState(false)

  useEffect(() => {
    let cancelled = false
    api
      .get<{ setup_required: boolean }>('/auth/setup-status')
      .then((res) => {
        if (!cancelled) {
          setChecked(true)
          if (res.data.setup_required) {
            navigate('/setup', { replace: true })
          } else {
            navigate('/dashboard', { replace: true })
          }
        }
      })
      .catch(() => {
        if (!cancelled) {
          setChecked(true)
          navigate('/dashboard', { replace: true })
        }
      })
    return () => {
      cancelled = true
    }
  }, [navigate])

  if (!checked) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-pulse h-8 w-8 rounded-full bg-brand-600" />
      </div>
    )
  }
  return null
}
