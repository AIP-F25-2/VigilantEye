import { Eye } from 'lucide-react'

const Logo = ({ size = 'md', showText = true }) => {
  const sizes = {
    sm: 'w-6 h-6',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
    xl: 'w-16 h-16',
  }

  const textSizes = {
    sm: 'text-xl',
    md: 'text-2xl',
    lg: 'text-3xl',
    xl: 'text-4xl',
  }

  return (
    <div className="flex items-center gap-3">
      <div className="relative">
        <Eye className={`${sizes[size]} text-primary-500`} strokeWidth={2} />
        <div className="absolute inset-0 bg-primary-500/20 blur-xl rounded-full animate-pulse-slow"></div>
      </div>
      {showText && (
        <div className={`font-bold ${textSizes[size]}`}>
          <span className="text-primary-500">Vigilant</span>
          <span className="text-gray-100">EYE</span>
        </div>
      )}
    </div>
  )
}

export default Logo
