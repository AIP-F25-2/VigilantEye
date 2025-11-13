import { useState, useEffect } from 'react'
import { Eye, EyeOff } from 'lucide-react'
import type { UseFormRegister, UseFormWatch } from 'react-hook-form'
import { cn } from '@/utils/cn'
import { PASSWORD_REQUIREMENTS, PASSWORD_REGEX } from '@/utils/constants'

interface PasswordInputProps {
  label: string
  name: string
  placeholder?: string
  error?: string
  register: UseFormRegister<any>
  watch?: UseFormWatch<any>
  required?: boolean
  disabled?: boolean
  className?: string
  showStrengthIndicator?: boolean
}

function calculatePasswordStrength(password: string): 'weak' | 'medium' | 'strong' {
  if (!password || password.length < 8) {
    return 'weak'
  }

  const hasUpper = PASSWORD_REGEX.UPPERCASE.test(password)
  const hasLower = PASSWORD_REGEX.LOWERCASE.test(password)
  const hasDigit = PASSWORD_REGEX.DIGIT.test(password)
  const hasSpecial = PASSWORD_REGEX.SPECIAL.test(password)

  const requirementsMet = [hasUpper, hasLower, hasDigit].filter(Boolean).length

  if (password.length >= 12 && hasUpper && hasLower && hasDigit && hasSpecial) {
    return 'strong'
  }

  if (password.length >= 8 && requirementsMet >= 3) {
    return 'medium'
  }

  return 'weak'
}

export function PasswordInput({
  label,
  name,
  placeholder,
  error,
  register,
  watch,
  required,
  disabled,
  className,
  showStrengthIndicator = false,
}: PasswordInputProps) {
  const [showPassword, setShowPassword] = useState(false)
  const [strength, setStrength] = useState<'weak' | 'medium' | 'strong'>('weak')

  const password = watch ? watch(name) : ''

  useEffect(() => {
    if (showStrengthIndicator && password) {
      setStrength(calculatePasswordStrength(password))
    }
  }, [password, showStrengthIndicator])

  const strengthColors = {
    weak: 'bg-red-500',
    medium: 'bg-yellow-500',
    strong: 'bg-green-500',
  }

  const strengthLabels = {
    weak: 'Weak',
    medium: 'Medium',
    strong: 'Strong',
  }

  return (
    <div className={className}>
      <label className="block text-sm font-medium text-gray-700">
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      <div className="relative mt-1">
        <input
          type={showPassword ? 'text' : 'password'}
          placeholder={placeholder}
          disabled={disabled}
          {...register(name)}
          className={cn(
            'block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm pr-10',
            error && 'border-red-500 focus:border-red-500 focus:ring-red-500',
            disabled && 'bg-gray-100 cursor-not-allowed'
          )}
        />
        <button
          type="button"
          onClick={() => setShowPassword(!showPassword)}
          className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600"
          aria-label={showPassword ? 'Hide password' : 'Show password'}
        >
          {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
        </button>
      </div>
      {showStrengthIndicator && password && (
        <div className="mt-2">
          <div className="flex items-center gap-2">
            <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={cn('h-full transition-all', strengthColors[strength])}
                style={{ width: strength === 'weak' ? '33%' : strength === 'medium' ? '66%' : '100%' }}
              />
            </div>
            <span className="text-xs text-gray-600">{strengthLabels[strength]}</span>
          </div>
        </div>
      )}
      {error && <p className="mt-1 text-sm text-red-600">{error}</p>}
    </div>
  )
}

