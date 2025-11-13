import { useAuth } from '@/hooks/useAuth'

interface RoleGuardProps {
  children: React.ReactNode
  role: 'admin' | 'staff'
  fallback?: React.ReactNode
}

export function RoleGuard({ children, role, fallback = null }: RoleGuardProps) {
  const { user } = useAuth()
  const hasRole = user?.role === role

  if (hasRole) {
    return <>{children}</>
  }

  return <>{fallback}</>
}

