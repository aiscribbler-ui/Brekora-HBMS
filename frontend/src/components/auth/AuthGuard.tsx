import { ReactNode, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'

export function AuthGuard({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuthStore()
  const navigate = useNavigate()

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login', { replace: true })
    }
  }, [isAuthenticated, navigate])

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-pulse h-8 w-8 rounded-full bg-brand-600" />
      </div>
    )
  }

  return <>{children}</>
}
