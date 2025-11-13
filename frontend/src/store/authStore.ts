import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User, AuthState } from '@/types/auth'

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isLoading: false,
      login: (user: User) => {
        set({ user, isLoading: false })
      },
      logout: () => {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        set({ user: null, isLoading: false })
      },
      setUser: (user: User | null) => {
        set({ user })
      },
      setLoading: (loading: boolean) => {
        set({ isLoading: loading })
      },
    }),
    {
      name: 'vigilanteye-auth',
      partialize: (state) => ({ user: state.user }),
    }
  )
)

// Derived selector for isAuthenticated
export const useIsAuthenticated = () => useAuthStore((state) => state.user !== null)

