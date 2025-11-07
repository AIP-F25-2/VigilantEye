import axios from 'axios'
import { useAuthStore } from '../store/authStore'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

// Create axios instance
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().accessToken
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    // Debug: Log request details for auth endpoints
    if (config.url?.includes('/auth/login') || config.url?.includes('/auth/signup')) {
      console.log('Request config:', {
        url: config.url,
        method: config.method,
        headers: config.headers,
        data: config.data,
      })
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    // If error is 401 and we haven't tried to refresh yet
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        const refreshToken = useAuthStore.getState().refreshToken
        if (refreshToken) {
          const response = await axios.post(`${API_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          })

          const { access_token } = response.data
          useAuthStore.getState().updateAccessToken(access_token)

          // Retry original request with new token
          originalRequest.headers.Authorization = `Bearer ${access_token}`
          return api(originalRequest)
        }
      } catch (refreshError) {
        // Refresh failed, logout user
        useAuthStore.getState().clearAuth()
        window.location.href = '/login'
        return Promise.reject(refreshError)
      }
    }

    return Promise.reject(error)
  }
)

// Auth API
export const authAPI = {
  signUp: async (data) => {
    // Debug: Log the request data
    console.log('SignUp request data:', data)
    console.log('SignUp request URL:', `${API_URL}/auth/signup`)
    
    const response = await api.post('/auth/signup', data)
    return response.data
  },

  login: async (data) => {
    // Debug: Log the request data
    console.log('Login request data:', data)
    console.log('Login request URL:', `${API_URL}/auth/login`)
    
    const response = await api.post('/auth/login', data)
    return response.data
  },

  getCurrentUser: async (accessToken = null) => {
    // If token is provided, use it directly; otherwise rely on interceptor
    const config = accessToken 
      ? { headers: { Authorization: `Bearer ${accessToken}` } }
      : {}
    const response = await api.get('/auth/me', config)
    return response.data
  },

  refreshToken: async (refreshToken) => {
    const response = await api.post('/auth/refresh', {
      refresh_token: refreshToken,
    })
    return response.data
  },
}

// Video API (for future use)
export const videoAPI = {
  uploadVideo: async (file, onProgress) => {
    const formData = new FormData()
    formData.append('file', file)

    const response = await api.post('/video/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        const percentCompleted = Math.round(
          (progressEvent.loaded * 100) / progressEvent.total
        )
        if (onProgress) {
          onProgress(percentCompleted)
        }
      },
    })
    return response.data
  },

  getVideos: async () => {
    const response = await api.get('/video/list')
    return response.data
  },

  getVideo: async (videoId) => {
    const response = await api.get(`/video/${videoId}`)
    return response.data
  },

  analyzeVideo: async (videoId) => {
    const response = await api.post(`/video/process/${videoId}`)
    return response.data
  },

  deleteVideo: async (videoId) => {
    const response = await api.delete(`/video/${videoId}`)
    return response.data
  },

  downloadVideo: async (videoId) => {
    const response = await api.get(`/video/${videoId}/download`, {
      responseType: 'blob'
    })
    return response.data
  },

  startStream: async (data) => {
    // Wrap data in metadata object as expected by backend
    const requestData = {
      metadata: data
    }
    const response = await api.post('/video/stream/start', requestData)
    return response.data
  },

  uploadChunk: async (videoId, chunk) => {
    const formData = new FormData()
    formData.append('chunk', chunk)
    
    const response = await api.post(`/video/stream/${videoId}/chunk`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  stopStream: async (videoId) => {
    const response = await api.post(`/video/stream/${videoId}/stop`)
    return response.data
  },
}

// Ticket API
export const ticketAPI = {
  getTickets: async (params = {}) => {
    const response = await api.get('/tickets', { params })
    return response.data
  },

  getTicket: async (ticketId) => {
    const response = await api.get(`/tickets/${ticketId}`)
    return response.data
  },

  acknowledgeTicket: async (ticketId, notes = null) => {
    const response = await api.post(`/tickets/${ticketId}/acknowledge`, { notes })
    return response.data
  },

  closeTicket: async (ticketId, notes = null) => {
    const response = await api.post(`/tickets/${ticketId}/close`, { notes })
    return response.data
  },

  addNote: async (ticketId, note) => {
    const response = await api.post(`/tickets/${ticketId}/note`, { note })
    return response.data
  },

  getTicketEvidence: async (ticketId) => {
    const response = await api.get(`/tickets/${ticketId}/evidence`)
    return response.data
  },

  getTicketStats: async () => {
    const response = await api.get('/tickets/stats/summary')
    return response.data
  },

  deleteEvidence: async (ticketId, evidenceId) => {
    const response = await api.delete(`/tickets/${ticketId}/evidence/${evidenceId}`)
    return response.data
  },

  deleteTicket: async (ticketId) => {
    const response = await api.delete(`/tickets/${ticketId}`)
    return response.data
  },

  downloadAllEvidence: async (ticketId) => {
    const response = await api.get(`/tickets/${ticketId}/evidence/download`, {
      responseType: 'blob'
    })
    return response.data
  },
}

export default api
