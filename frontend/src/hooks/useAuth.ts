import { useAuthStore } from '@/store/authStore'
import type { User } from '@/types/auth'
import { USER_ROLES } from '@/utils/constants'

export function useAuth() {
  const user = useAuthStore((state) => state.user)
  const isAuthenticated = user !== null
  const isLoading = useAuthStore((state) => state.isLoading)
  const login = useAuthStore((state) => state.login)
  const logout = useAuthStore((state) => state.logout)

  return {
    user,
    isAuthenticated,
    isLoading,
    isAdmin: user?.role === USER_ROLES.ADMIN,
    isStaff: user?.role === USER_ROLES.STAFF,
    login,
    logout,
  }
}

