import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { ROUTES } from '@/utils/constants'

interface ProtectedRouteProps {
  children: React.ReactNode
  requiredRole?: 'admin' | 'staff'
}

export function ProtectedRoute({ children, requiredRole }: ProtectedRouteProps) {
  const { user, isAuthenticated, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to={ROUTES.LOGIN} state={{ from: location.pathname }} replace />
  }

  if (requiredRole && user) {
    if (requiredRole === 'admin' && user.role !== 'admin') {
      console.warn('Access denied: insufficient permissions')
      return <Navigate to={ROUTES.HOME} replace />
    }
    if (requiredRole === 'staff' && user.role !== 'staff' && user.role !== 'admin') {
      console.warn('Access denied: insufficient permissions')
      return <Navigate to={ROUTES.HOME} replace />
    }
  }

  return <>{children}</>
}

