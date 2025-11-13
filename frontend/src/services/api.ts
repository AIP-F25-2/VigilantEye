import axios, { type AxiosError, type AxiosRequestConfig } from 'axios'
import { API_BASE_URL } from '@/utils/constants'

type RetriableRequestConfig = AxiosRequestConfig & { _retry?: boolean }

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers = {
        ...config.headers,
        Authorization: `Bearer ${token}`,
      }
    }
    return config
  },
  error => Promise.reject(error)
)

api.interceptors.response.use(
  response => response,
  async error => {
    const originalRequest = error.config as RetriableRequestConfig | undefined

    if (!originalRequest) {
      return Promise.reject(error)
    }

    if ((error as AxiosError).response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        const refreshToken = localStorage.getItem('refresh_token')
        const response = await axios.post<{ access_token: string; refresh_token?: string }>(
          `${API_BASE_URL}/auth/refresh`,
          {
            refresh_token: refreshToken,
          }
        )

        const { access_token: accessToken, refresh_token: newRefreshToken } = response.data
        localStorage.setItem('access_token', accessToken)
        
        // Persist refresh token if rotation is provided
        if (newRefreshToken) {
          localStorage.setItem('refresh_token', newRefreshToken)
        }

        // Dispatch event to notify token refresh for auto-logout recalculation
        window.dispatchEvent(new CustomEvent('auth:tokenRefreshed', { 
          detail: { access_token: accessToken } 
        }))

        originalRequest.headers = {
          ...originalRequest.headers,
          Authorization: `Bearer ${accessToken}`,
        }

        return api(originalRequest)
      } catch (refreshError) {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
        return Promise.reject(refreshError)
      }
    }

    return Promise.reject(error)
  }
)

export default api

