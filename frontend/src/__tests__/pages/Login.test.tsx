import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import { LoginPage } from '@/pages/Login'
import * as authService from '@/services/authService'
import { useAuth } from '@/hooks/useAuth'

const mockNavigate = vi.fn()
let mockLocation = { state: null, pathname: '/login', search: '', hash: '' }

// Mock dependencies
vi.mock('@/services/authService')
vi.mock('@/hooks/useAuth')
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useLocation: () => mockLocation,
  }
})

// Test wrapper component
const TestWrapper = ({ children }: { children: React.ReactNode }) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Toaster />
        {children}
      </BrowserRouter>
    </QueryClientProvider>
  )
}

describe('Login Page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(useAuth as any).mockReturnValue({
      isAuthenticated: false,
      login: vi.fn(),
    })
  })

  it('renders login form with username and password fields', () => {
    render(
      <TestWrapper>
        <LoginPage />
      </TestWrapper>
    )

    expect(screen.getByLabelText(/email or username/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })

  it('shows validation error for empty username', async () => {
    render(
      <TestWrapper>
        <LoginPage />
      </TestWrapper>
    )

    const submitButton = screen.getByRole('button', { name: /sign in/i })
    fireEvent.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText(/username is required/i)).toBeInTheDocument()
    })
  })

  it('shows validation error for empty password', async () => {
    render(
      <TestWrapper>
        <LoginPage />
      </TestWrapper>
    )

    const usernameInput = screen.getByLabelText(/email or username/i)
    fireEvent.change(usernameInput, { target: { value: 'testuser' } })

    const submitButton = screen.getByRole('button', { name: /sign in/i })
    fireEvent.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText(/password is required/i)).toBeInTheDocument()
    })
  })

  it('calls authService.login with correct credentials', async () => {
    const mockLogin = vi.spyOn(authService, 'login').mockResolvedValue({
      access_token: 'token123',
      refresh_token: 'refresh123',
      user: {
        id: '123',
        username: 'testuser',
        email: 'test@example.com',
        role: 'staff',
        is_active: true,
        last_login: null,
        created_at: new Date().toISOString(),
      },
      expires_in: 3600,
    })

    render(
      <TestWrapper>
        <LoginPage />
      </TestWrapper>
    )

    const usernameInput = screen.getByLabelText(/email or username/i)
    const passwordInput = screen.getByLabelText(/password/i)
    const submitButton = screen.getByRole('button', { name: /sign in/i })

    fireEvent.change(usernameInput, { target: { value: 'testuser' } })
    fireEvent.change(passwordInput, { target: { value: 'Password123' } })
    fireEvent.click(submitButton)

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith({
        username: 'testuser',
        password: 'Password123',
      })
    })
  })

  it('stores tokens in localStorage on successful login', async () => {
    const mockSetItem = vi.spyOn(Storage.prototype, 'setItem')
    vi.spyOn(authService, 'login').mockResolvedValue({
      access_token: 'token123',
      refresh_token: 'refresh123',
      user: {
        id: '123',
        username: 'testuser',
        email: 'test@example.com',
        role: 'staff',
        is_active: true,
        last_login: null,
        created_at: new Date().toISOString(),
      },
      expires_in: 3600,
    })

    render(
      <TestWrapper>
        <LoginPage />
      </TestWrapper>
    )

    const usernameInput = screen.getByLabelText(/email or username/i)
    const passwordInput = screen.getByLabelText(/password/i)
    const submitButton = screen.getByRole('button', { name: /sign in/i })

    fireEvent.change(usernameInput, { target: { value: 'testuser' } })
    fireEvent.change(passwordInput, { target: { value: 'Password123' } })
    fireEvent.click(submitButton)

    await waitFor(() => {
      expect(mockSetItem).toHaveBeenCalledWith('access_token', 'token123')
      expect(mockSetItem).toHaveBeenCalledWith('refresh_token', 'refresh123')
    })
  })

  it('shows error toast on login failure', async () => {
    vi.spyOn(authService, 'login').mockRejectedValue({
      response: {
        data: { error: 'Invalid credentials' },
      },
    })

    render(
      <TestWrapper>
        <LoginPage />
      </TestWrapper>
    )

    const usernameInput = screen.getByLabelText(/email or username/i)
    const passwordInput = screen.getByLabelText(/password/i)
    const submitButton = screen.getByRole('button', { name: /sign in/i })

    fireEvent.change(usernameInput, { target: { value: 'testuser' } })
    fireEvent.change(passwordInput, { target: { value: 'wrongpassword' } })
    fireEvent.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument()
    })
  })

  it('shows rate limit error (429)', async () => {
    vi.spyOn(authService, 'login').mockRejectedValue({
      response: {
        status: 429,
        data: { error: 'Too many attempts' },
      },
    })

    render(
      <TestWrapper>
        <LoginPage />
      </TestWrapper>
    )

    const usernameInput = screen.getByLabelText(/email or username/i)
    const passwordInput = screen.getByLabelText(/password/i)
    const submitButton = screen.getByRole('button', { name: /sign in/i })

    fireEvent.change(usernameInput, { target: { value: 'testuser' } })
    fireEvent.change(passwordInput, { target: { value: 'Password123' } })
    fireEvent.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText(/too many attempts/i)).toBeInTheDocument()
    })
  })

  it('disables form during submission', async () => {
    let resolveLogin: (value: any) => void
    const loginPromise = new Promise((resolve) => {
      resolveLogin = resolve
    })

    vi.spyOn(authService, 'login').mockReturnValue(loginPromise as any)

    render(
      <TestWrapper>
        <LoginPage />
      </TestWrapper>
    )

    const usernameInput = screen.getByLabelText(/email or username/i)
    const passwordInput = screen.getByLabelText(/password/i)
    const submitButton = screen.getByRole('button', { name: /sign in/i })

    fireEvent.change(usernameInput, { target: { value: 'testuser' } })
    fireEvent.change(passwordInput, { target: { value: 'Password123' } })
    fireEvent.click(submitButton)

    await waitFor(() => {
      expect(submitButton).toBeDisabled()
    })

    // Resolve the promise
    resolveLogin!({
      access_token: 'token',
      refresh_token: 'refresh',
      user: {
        id: '123',
        username: 'testuser',
        email: 'test@example.com',
        role: 'staff',
        is_active: true,
        last_login: null,
        created_at: new Date().toISOString(),
      },
      expires_in: 3600,
    })
  })

  it('redirects to home if already authenticated', async () => {
    ;(useAuth as any).mockReturnValue({
      isAuthenticated: true,
      login: vi.fn(),
    })

    render(
      <TestWrapper>
        <LoginPage />
      </TestWrapper>
    )

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true })
    })
  })

  it('navigates to location.state.from after successful login', async () => {
    // Set location with state
    const originalLocation = mockLocation
    mockLocation = {
      state: { from: '/protected-page' },
      pathname: '/login',
      search: '',
      hash: '',
    }

    vi.spyOn(authService, 'login').mockResolvedValue({
      access_token: 'token123',
      refresh_token: 'refresh123',
      user: {
        id: '123',
        username: 'testuser',
        email: 'test@example.com',
        role: 'staff',
        is_active: true,
        last_login: null,
        created_at: new Date().toISOString(),
      },
      expires_in: 3600,
    })

    render(
      <TestWrapper>
        <LoginPage />
      </TestWrapper>
    )

    const usernameInput = screen.getByLabelText(/email or username/i)
    const passwordInput = screen.getByLabelText(/password/i)
    const submitButton = screen.getByRole('button', { name: /sign in/i })

    fireEvent.change(usernameInput, { target: { value: 'testuser' } })
    fireEvent.change(passwordInput, { target: { value: 'Password123' } })
    fireEvent.click(submitButton)

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/protected-page', { replace: true })
    })

    // Reset the location
    mockLocation = originalLocation
  })

  it('toggles password visibility via eye icon', async () => {
    render(
      <TestWrapper>
        <LoginPage />
      </TestWrapper>
    )

    const passwordInput = screen.getByLabelText(/password/i) as HTMLInputElement
    const toggleButton = screen.getByRole('button', { name: /show password|hide password/i })

    // Password should be hidden initially
    expect(passwordInput.type).toBe('password')

    // Click to show password
    fireEvent.click(toggleButton)
    await waitFor(() => {
      expect(passwordInput.type).toBe('text')
    })

    // Click to hide password again
    fireEvent.click(toggleButton)
    await waitFor(() => {
      expect(passwordInput.type).toBe('password')
    })
  })
})
