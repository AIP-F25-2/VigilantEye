import { describe, it, expect, beforeEach, vi } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useAuth } from '@/hooks/useAuth'
import { useAuthStore } from '@/store/authStore'

// Mock the store
vi.mock('@/store/authStore', () => ({
  useAuthStore: vi.fn(),
}))

describe('useAuth Hook', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('returns initial state (not authenticated)', () => {
    ;(useAuthStore as any).mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    })

    const { result } = renderHook(() => useAuth())

    expect(result.current.user).toBeNull()
    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.isAdmin).toBe(false)
    expect(result.current.isStaff).toBe(false)
  })

  it('returns user when authenticated', () => {
    const mockUser = {
      id: '123',
      username: 'test',
      email: 'test@example.com',
      role: 'staff' as const,
      is_active: true,
      last_login: null,
      created_at: new Date().toISOString(),
    }

    ;(useAuthStore as any).mockReturnValue({
      user: mockUser,
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    })

    const { result } = renderHook(() => useAuth())

    expect(result.current.user).not.toBeNull()
    expect(result.current.isAuthenticated).toBe(true)
    expect(result.current.isStaff).toBe(true)
  })

  it('identifies admin user', () => {
    const mockAdminUser = {
      id: '123',
      username: 'admin',
      email: 'admin@example.com',
      role: 'admin' as const,
      is_active: true,
      last_login: null,
      created_at: new Date().toISOString(),
    }

    ;(useAuthStore as any).mockReturnValue({
      user: mockAdminUser,
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    })

    const { result } = renderHook(() => useAuth())

    expect(result.current.isAdmin).toBe(true)
    expect(result.current.isStaff).toBe(false)
  })

  it('login action updates state', () => {
    const mockLogin = vi.fn()
    ;(useAuthStore as any).mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      login: mockLogin,
      logout: vi.fn(),
    })

    const { result } = renderHook(() => useAuth())

    const mockUser = {
      id: '123',
      username: 'test',
      email: 'test@example.com',
      role: 'staff' as const,
      is_active: true,
      last_login: null,
      created_at: new Date().toISOString(),
    }

    result.current.login(mockUser)

    expect(mockLogin).toHaveBeenCalledWith(mockUser)
  })

  it('logout action clears state', () => {
    const mockLogout = vi.fn()
    const mockUser = {
      id: '123',
      username: 'test',
      email: 'test@example.com',
      role: 'staff' as const,
      is_active: true,
      last_login: null,
      created_at: new Date().toISOString(),
    }

    ;(useAuthStore as any).mockReturnValue({
      user: mockUser,
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: mockLogout,
    })

    const { result } = renderHook(() => useAuth())

    result.current.logout()

    expect(mockLogout).toHaveBeenCalled()
  })
})
