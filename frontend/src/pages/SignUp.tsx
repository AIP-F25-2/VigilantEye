import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useNavigate, Link } from 'react-router-dom'
import { Eye } from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuth } from '@/hooks/useAuth'
import { authService } from '@/services/authService'
import { FormInput } from '@/components/FormInput'
import { PasswordInput } from '@/components/PasswordInput'
import { Button } from '@/components/Button'
import { ROUTES, PASSWORD_REQUIREMENTS, PASSWORD_REGEX } from '@/utils/constants'
import type { SignUpData } from '@/types/auth'

const signupSchema = z
  .object({
    username: z
      .string()
      .min(3, 'Username must be at least 3 characters')
      .max(80, 'Username too long')
      .regex(/^[a-zA-Z0-9_]+$/, 'Username can only contain letters, numbers, and underscores'),
    email: z.string().email('Invalid email address'),
    password: z
      .string()
      .min(PASSWORD_REQUIREMENTS.MIN_LENGTH, `Password must be at least ${PASSWORD_REQUIREMENTS.MIN_LENGTH} characters`)
      .regex(PASSWORD_REGEX.UPPERCASE, 'Password must contain at least one uppercase letter')
      .regex(PASSWORD_REGEX.LOWERCASE, 'Password must contain at least one lowercase letter')
      .regex(PASSWORD_REGEX.DIGIT, 'Password must contain at least one digit'),
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  })

export function SignUpPage() {
  const navigate = useNavigate()
  const { isAuthenticated } = useAuth()

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<SignUpData>({
    resolver: zodResolver(signupSchema),
  })

  const password = watch('password')

  useEffect(() => {
    if (isAuthenticated) {
      navigate(ROUTES.HOME, { replace: true })
    }
  }, [isAuthenticated, navigate])

  const onSubmit = async (data: SignUpData) => {
    try {
      await authService.signup(data)
      toast.success('Account created successfully! Please sign in.')
      navigate(ROUTES.LOGIN)
    } catch (error: any) {
      const errorMessage =
        error.response?.data?.error || error.message || 'Signup failed'
      
      if (error.response?.status === 409) {
        toast.error('Username or email already exists')
      } else {
        toast.error(errorMessage)
      }
    }
  }

  const checkRequirement = (regex: RegExp, minLength?: number) => {
    if (!password) return false
    if (minLength && password.length < minLength) return false
    return regex.test(password)
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50">
      <div className="w-full max-w-md">
        <div className="bg-white shadow-md rounded-lg p-8">
          <div className="flex items-center justify-center mb-6">
            <Eye className="h-8 w-8 text-primary-600 mr-2" />
            <h1 className="text-2xl font-bold text-gray-900">VigilentEye</h1>
          </div>
          <p className="text-center text-gray-600 mb-6">Create your account</p>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            <FormInput
              label="Username"
              name="username"
              placeholder="Enter your username"
              register={register}
              error={errors.username?.message}
              required
              autoComplete="username"
            />

            <FormInput
              label="Email"
              name="email"
              type="email"
              placeholder="you@example.com"
              register={register}
              error={errors.email?.message}
              required
              autoComplete="email"
            />

            <PasswordInput
              label="Password"
              name="password"
              placeholder="Enter your password"
              register={register}
              watch={watch}
              error={errors.password?.message}
              required
              autoComplete="new-password"
              showStrengthIndicator
            />

            {password && (
              <div className="text-sm text-gray-600 space-y-1">
                <div className={checkRequirement(/./, PASSWORD_REQUIREMENTS.MIN_LENGTH) ? 'text-green-600' : ''}>
                  {checkRequirement(/./, PASSWORD_REQUIREMENTS.MIN_LENGTH) ? '✓' : '○'} At least {PASSWORD_REQUIREMENTS.MIN_LENGTH} characters
                </div>
                <div className={checkRequirement(PASSWORD_REGEX.UPPERCASE) ? 'text-green-600' : ''}>
                  {checkRequirement(PASSWORD_REGEX.UPPERCASE) ? '✓' : '○'} One uppercase letter
                </div>
                <div className={checkRequirement(PASSWORD_REGEX.LOWERCASE) ? 'text-green-600' : ''}>
                  {checkRequirement(PASSWORD_REGEX.LOWERCASE) ? '✓' : '○'} One lowercase letter
                </div>
                <div className={checkRequirement(PASSWORD_REGEX.DIGIT) ? 'text-green-600' : ''}>
                  {checkRequirement(PASSWORD_REGEX.DIGIT) ? '✓' : '○'} One digit
                </div>
              </div>
            )}

            <PasswordInput
              label="Confirm Password"
              name="confirmPassword"
              placeholder="Confirm your password"
              register={register}
              error={errors.confirmPassword?.message}
              required
              autoComplete="new-password"
            />

            <Button type="submit" isLoading={isSubmitting} fullWidth>
              Create Account
            </Button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-sm text-gray-600">
              Already have an account?{' '}
              <Link
                to={ROUTES.LOGIN}
                className="text-primary-600 hover:text-primary-500 font-medium"
              >
                Sign in
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

