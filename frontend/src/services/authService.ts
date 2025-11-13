import type { AxiosError } from 'axios'
import api from './api'
import type { User, AuthResponse, LoginCredentials, SignUpData } from '@/types/auth'
import { useAuthStore } from '@/store/authStore'

export const authService = {
  async signup(data: SignUpData): Promise<User> {
    const response = await api.post<{ user: User }>('/auth/signup', {
      username: data.username,
      email: data.email,
      password: data.password,
    })
    return response.data.user
  },

  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    const response = await api.post<AuthResponse>('/auth/login', credentials)
    const { access_token, refresh_token, user, expires_in } = response.data

    localStorage.setItem('access_token', access_token)
    localStorage.setItem('refresh_token', refresh_token)

    return response.data
  },

  async logout(): Promise<void> {
    try {
      await api.post('/auth/logout')
    } catch (error) {
      // Even if logout API fails, clear local tokens
      console.error('Logout API error:', error)
    } finally {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      useAuthStore.getState().logout()
    }
  },

  async refreshToken(): Promise<string> {
    const refreshToken = localStorage.getItem('refresh_token')
    if (!refreshToken) {
      throw new Error('No refresh token available')
    }

    const response = await api.post<{ access_token: string; refresh_token?: string }>('/auth/refresh', {
      refresh_token: refreshToken,
    })

    const { access_token, refresh_token } = response.data
    localStorage.setItem('access_token', access_token)
    
    // Persist refresh token if rotation is provided
    if (refresh_token) {
      localStorage.setItem('refresh_token', refresh_token)
    }

    // Dispatch event to notify token refresh for auto-logout recalculation
    window.dispatchEvent(new CustomEvent('auth:tokenRefreshed', { 
      detail: { access_token } 
    }))

    return access_token
  },

  async getCurrentUser(): Promise<User> {
    const response = await api.get<{ user: User }>('/auth/me')
    return response.data.user
  },

  async checkAuthStatus(): Promise<boolean> {
    const accessToken = localStorage.getItem('access_token')
    if (!accessToken) {
      return false
    }

    try {
      const user = await this.getCurrentUser()
      useAuthStore.getState().setUser(user)
      return true
    } catch (error) {
      const axiosError = error as AxiosError
      if (axiosError.response?.status === 401) {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        useAuthStore.getState().setUser(null)
      }
      return false
    }
  },

  async getUsers(): Promise<User[]> {
    const response = await api.get<{ users: User[] }>('/auth/users')
    return response.data.users
  },
}

