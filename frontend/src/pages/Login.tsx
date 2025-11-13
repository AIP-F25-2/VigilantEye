import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import { Eye } from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuth } from '@/hooks/useAuth'
import { authService } from '@/services/authService'
import { FormInput } from '@/components/FormInput'
import { PasswordInput } from '@/components/PasswordInput'
import { Button } from '@/components/Button'
import { ROUTES } from '@/utils/constants'
import type { LoginCredentials } from '@/types/auth'

const loginSchema = z.object({
  username: z.string().min(1, 'Email or username is required').refine(
    (val) => {
      // Accept either a valid email or a non-empty string (username)
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
      return emailRegex.test(val) || val.trim().length > 0
    },
    {
      message: 'Please enter a valid email or username',
    }
  ),
  password: z.string().min(1, 'Password is required'),
})

export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { isAuthenticated, login: setAuthUser } = useAuth()

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginCredentials>({
    resolver: zodResolver(loginSchema),
  })

  useEffect(() => {
    if (isAuthenticated) {
      navigate(ROUTES.HOME, { replace: true })
    }
  }, [isAuthenticated, navigate])

  const onSubmit = async (data: LoginCredentials) => {
    try {
      const response = await authService.login(data)
      setAuthUser(response.user)
      toast.success('Welcome back!')
      const returnUrl = (location.state as any)?.from || ROUTES.HOME
      navigate(returnUrl, { replace: true })
    } catch (error: any) {
      const errorMessage =
        error.response?.data?.error || error.message || 'Login failed'
      
      if (error.response?.status === 429) {
        toast.error('Too many attempts, try again later')
      } else {
        toast.error(errorMessage)
      }
    }
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50">
      <div className="w-full max-w-md">
        <div className="bg-white shadow-md rounded-lg p-8">
          <div className="flex items-center justify-center mb-6">
            <Eye className="h-8 w-8 text-primary-600 mr-2" />
            <h1 className="text-2xl font-bold text-gray-900">VigilentEye</h1>
          </div>
          <p className="text-center text-gray-600 mb-6">Sign in to your account</p>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            <FormInput
              label="Email or Username"
              name="username"
              placeholder="Enter your email or username"
              register={register}
              error={errors.username?.message}
              required
              autoComplete="username"
            />

            <PasswordInput
              label="Password"
              name="password"
              placeholder="Enter your password"
              register={register}
              error={errors.password?.message}
              required
              autoComplete="current-password"
            />

            <Button type="submit" isLoading={isSubmitting} fullWidth>
              Sign In
            </Button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-sm text-gray-600">
              Don't have an account?{' '}
              <Link
                to={ROUTES.SIGNUP}
                className="text-primary-600 hover:text-primary-500 font-medium"
              >
                Sign up
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

