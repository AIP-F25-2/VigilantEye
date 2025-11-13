import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from './useAuth'
import { ROUTES } from '@/utils/constants'

export function useRequireAuth(requiredRole?: 'admin' | 'staff') {
  const { user, isAuthenticated, isLoading } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    if (isLoading) return

    if (!isAuthenticated) {
      const returnUrl = window.location.pathname
      navigate(ROUTES.LOGIN, { state: { returnUrl } })
      return
    }

    if (requiredRole && user) {
      if (requiredRole === 'admin' && user.role !== 'admin') {
        navigate(ROUTES.HOME)
        return
      }
      if (requiredRole === 'staff' && user.role !== 'staff' && user.role !== 'admin') {
        navigate(ROUTES.HOME)
        return
      }
    }
  }, [isAuthenticated, isLoading, user, requiredRole, navigate])

  return { user, isLoading }
}

