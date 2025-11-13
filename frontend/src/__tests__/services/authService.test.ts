import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import axios from 'axios'
import * as authService from '@/services/authService'

// Mock axios
vi.mock('axios')
const mockedAxios = axios as any

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
}
global.localStorage = localStorageMock as any

// Mock authStore
vi.mock('@/store/authStore', () => ({
  useAuthStore: {
    getState: () => ({
      logout: vi.fn(),
    }),
  },
}))

describe('authService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('signup', () => {
    it('calls API with correct data', async () => {
      const mockUser = {
        id: '123',
        username: 'test',
        email: 'test@example.com',
        role: 'staff',
        is_active: true,
        last_login: null,
        created_at: new Date().toISOString(),
      }

      mockedAxios.post.mockResolvedValue({
        data: { user: mockUser },
      })

      const result = await authService.authService.signup({
        username: 'test',
        email: 'test@example.com',
        password: 'Password123',
      })

      expect(mockedAxios.post).toHaveBeenCalledWith('/auth/signup', {
        username: 'test',
        email: 'test@example.com',
        password: 'Password123',
      })
      expect(result).toEqual(mockUser)
    })

    it('throws error on duplicate username (409)', async () => {
      mockedAxios.post.mockRejectedValue({
        response: {
          status: 409,
          data: { error: 'Username exists' },
        },
      })

      await expect(
        authService.authService.signup({
          username: 'test',
          email: 'test@example.com',
          password: 'Password123',
        })
      ).rejects.toThrow()
    })
  })

  describe('login', () => {
    it('calls API and stores tokens', async () => {
      const mockResponse = {
        access_token: 'token123',
        refresh_token: 'refresh123',
        user: {
          id: '123',
          username: 'test',
          email: 'test@example.com',
          role: 'staff',
          is_active: true,
          last_login: null,
          created_at: new Date().toISOString(),
        },
        expires_in: 3600,
      }

      mockedAxios.post.mockResolvedValue({
        data: mockResponse,
      })

      const result = await authService.authService.login({
        username: 'test',
        password: 'Password123',
      })

      expect(mockedAxios.post).toHaveBeenCalledWith('/auth/login', {
        username: 'test',
        password: 'Password123',
      })
      expect(localStorageMock.setItem).toHaveBeenCalledWith('access_token', 'token123')
      expect(localStorageMock.setItem).toHaveBeenCalledWith('refresh_token', 'refresh123')
      expect(result).toEqual(mockResponse)
    })

    it('throws error on invalid credentials (401)', async () => {
      mockedAxios.post.mockRejectedValue({
        response: {
          status: 401,
          data: { error: 'Invalid credentials' },
        },
      })

      await expect(
        authService.authService.login({
          username: 'test',
          password: 'wrongpassword',
        })
      ).rejects.toThrow()
    })
  })

  describe('logout', () => {
    it('calls API and clears tokens', async () => {
      mockedAxios.post.mockResolvedValue({ data: {} })

      await authService.authService.logout()

      expect(mockedAxios.post).toHaveBeenCalledWith('/auth/logout')
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('access_token')
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('refresh_token')
    })

    it('clears tokens even if API fails', async () => {
      mockedAxios.post.mockRejectedValue(new Error('Network error'))

      await authService.authService.logout()

      expect(localStorageMock.removeItem).toHaveBeenCalledWith('access_token')
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('refresh_token')
    })
  })

  describe('refreshToken', () => {
    it('calls API with refresh token and updates localStorage', async () => {
      localStorageMock.getItem.mockReturnValue('refresh123')
      mockedAxios.post.mockResolvedValue({
        data: {
          access_token: 'new_token123',
          refresh_token: 'new_refresh123',
        },
      })

      await authService.authService.refreshToken()

      expect(mockedAxios.post).toHaveBeenCalledWith('/auth/refresh', {
        refresh_token: 'refresh123',
      })
      expect(localStorageMock.setItem).toHaveBeenCalledWith('access_token', 'new_token123')
      expect(localStorageMock.setItem).toHaveBeenCalledWith('refresh_token', 'new_refresh123')
    })
  })

  describe('getCurrentUser', () => {
    it('calls API and returns user', async () => {
      const mockUser = {
        id: '123',
        username: 'test',
        email: 'test@example.com',
        role: 'staff',
        is_active: true,
        last_login: null,
        created_at: new Date().toISOString(),
      }

      mockedAxios.get.mockResolvedValue({
        data: { user: mockUser },
      })

      const result = await authService.authService.getCurrentUser()

      expect(mockedAxios.get).toHaveBeenCalledWith('/auth/me')
      expect(result).toEqual(mockUser)
    })

    it('throws error on 401', async () => {
      mockedAxios.get.mockRejectedValue({
        response: {
          status: 401,
          data: { error: 'Unauthorized' },
        },
      })

      await expect(authService.authService.getCurrentUser()).rejects.toThrow()
    })
  })
})
