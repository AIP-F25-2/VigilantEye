import type { UseFormRegister } from 'react-hook-form'
import { cn } from '@/utils/cn'

interface FormInputProps {
  label: string
  name: string
  type?: string
  placeholder?: string
  error?: string
  register: UseFormRegister<any>
  required?: boolean
  disabled?: boolean
  autoComplete?: string
  className?: string
}

export function FormInput({
  label,
  name,
  type = 'text',
  placeholder,
  error,
  register,
  required,
  disabled,
  autoComplete,
  className,
}: FormInputProps) {
  return (
    <div className={className}>
      <label className="block text-sm font-medium text-gray-700">
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      <input
        type={type}
        placeholder={placeholder}
        autoComplete={autoComplete}
        disabled={disabled}
        {...register(name)}
        className={cn(
          'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
          error && 'border-red-500 focus:border-red-500 focus:ring-red-500',
          disabled && 'bg-gray-100 cursor-not-allowed'
        )}
      />
      {error && <p className="mt-1 text-sm text-red-600">{error}</p>}
    </div>
  )
}

