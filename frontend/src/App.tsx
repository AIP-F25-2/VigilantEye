import { useEffect } from 'react'
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { LoginPage } from '@/pages/Login'
import { SignUpPage } from '@/pages/SignUp'
import HomePage from '@/pages/Home'
import VideoDirectoryPage from '@/pages/VideoDirectory'
import TicketsPage from '@/pages/Tickets'
import AnalyticsPage from '@/pages/Analytics'
import { ProtectedRoute } from '@/components/ProtectedRoute'
import { useAuthStore } from '@/store/authStore'
import { authService } from '@/services/authService'
import { getTimeUntilExpiration } from '@/utils/tokenUtils'
import { ROUTES } from '@/utils/constants'

function App() {
  const navigate = useNavigate()
  const setUser = useAuthStore((state) => state.setUser)
  const setLoading = useAuthStore((state) => state.setLoading)
  const logout = useAuthStore((state) => state.logout)
  const isLoading = useAuthStore((state) => state.isLoading)
  const user = useAuthStore((state) => state.user)

  useEffect(() => {
    const initializeAuth = async () => {
      // Initialize isLoading to true if access_token exists to prevent race condition
      const accessToken = localStorage.getItem('access_token')
      if (!accessToken) {
        setLoading(false)
        return
      }
      
      setLoading(true)
      try {
        const user = await authService.getCurrentUser()
        setUser(user)
      } catch (error) {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        setUser(null)
      } finally {
        setLoading(false)
      }
    }

    initializeAuth()
  }, [setUser, setLoading])

  // Auto-logout timer effect - recalculates when token changes
  useEffect(() => {
    const accessToken = localStorage.getItem('access_token')
    if (!accessToken) return

    const scheduleLogout = (): NodeJS.Timeout | null => {
      const currentToken = localStorage.getItem('access_token')
      if (!currentToken) return null

      const timeUntilExpiration = getTimeUntilExpiration(currentToken)
      if (timeUntilExpiration <= 0) {
        logout()
        navigate(ROUTES.LOGIN)
        toast.info('Session expired, please login again')
        return null
      }

      const logoutTime = Math.max(0, timeUntilExpiration - 60000) // 1 minute before expiration

      return setTimeout(() => {
        logout()
        navigate(ROUTES.LOGIN)
        toast.info('Session expired, please login again')
      }, logoutTime)
    }

    let timer: NodeJS.Timeout | null = scheduleLogout()

    // Listen for token refresh events to recalculate timer
    const handleTokenRefresh = () => {
      if (timer) {
        clearTimeout(timer)
      }
      timer = scheduleLogout()
    }

    // Listen for storage changes (token updates)
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'access_token') {
        if (timer) {
          clearTimeout(timer)
        }
        timer = scheduleLogout()
      }
    }

    window.addEventListener('auth:tokenRefreshed', handleTokenRefresh)
    window.addEventListener('storage', handleStorageChange)

    return () => {
      if (timer) {
        clearTimeout(timer)
      }
      window.removeEventListener('auth:tokenRefreshed', handleTokenRefresh)
      window.removeEventListener('storage', handleStorageChange)
    }
  }, [logout, navigate, user])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignUpPage />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <HomePage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/videos"
          element={
            <ProtectedRoute>
              <VideoDirectoryPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/tickets"
          element={
            <ProtectedRoute>
              <TicketsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/analytics"
          element={
            <ProtectedRoute>
              <AnalyticsPage />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  )
}

export default App

