export interface User {
  id: string
  username: string
  email: string
  role: 'staff' | 'admin'
  is_active: boolean
  last_login: string | null
  created_at: string
}

export interface AuthResponse {
  access_token: string
  refresh_token: string
  user: User
  expires_in: number
}

export interface LoginCredentials {
  username: string
  password: string
}

export interface SignUpData {
  username: string
  email: string
  password: string
  confirmPassword: string
}

export interface AuthState {
  user: User | null
  isLoading: boolean
  login: (user: User) => void
  logout: () => void
  setUser: (user: User | null) => void
  setLoading: (loading: boolean) => void
}

