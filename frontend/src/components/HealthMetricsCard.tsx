import { TrendingUp, TrendingDown } from 'lucide-react'
import { cn } from '@/utils/cn'

interface HealthMetricsCardProps {
  title: string
  value: number | string | undefined
  unit?: string
  status: 'healthy' | 'warning' | 'error'
  icon: React.ReactNode
  trend?: {
    direction: 'up' | 'down'
    percentage: number
  }
  subtitle?: string
}

export function HealthMetricsCard({
  title,
  value,
  unit,
  status,
  icon,
  trend,
  subtitle,
}: HealthMetricsCardProps) {
  const statusBgClass = {
    healthy: 'bg-green-100',
    warning: 'bg-yellow-100',
    error: 'bg-red-100',
  }[status]

  const statusDotClass = {
    healthy: 'bg-green-500',
    warning: 'bg-yellow-500',
    error: 'bg-red-500',
  }[status]

  const statusText = {
    healthy: 'Healthy',
    warning: 'Warning',
    error: 'Error',
  }[status]

  const trendColorClass = trend?.direction === 'up' ? 'text-red-600' : 'text-green-600'

  return (
    <div className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
      <div className="flex items-center justify-between mb-4">
        <div className={cn('p-3 rounded-full', statusBgClass)}>{icon}</div>
        <div className="flex items-center gap-2">
          <div className={cn('w-2 h-2 rounded-full', statusDotClass)} />
          <span className="text-xs text-gray-600">{statusText}</span>
        </div>
      </div>
      <h3 className="text-sm font-medium text-gray-600 mb-2">{title}</h3>
      <p className="text-3xl font-bold text-gray-900">
        {value !== undefined ? (
          <>
            {value}
            {unit && <span className="text-lg text-gray-500 ml-1">{unit}</span>}
          </>
        ) : (
          <span className="text-lg text-gray-400">N/A</span>
        )}
      </p>
      {trend && (
        <div className="flex items-center gap-1 mt-2">
          {trend.direction === 'up' ? (
            <TrendingUp className="w-4 h-4 text-red-600" />
          ) : (
            <TrendingDown className="w-4 h-4 text-green-600" />
          )}
          <span className={cn('text-sm', trendColorClass)}>
            {trend.direction === 'up' ? '↑' : '↓'} {trend.percentage}%
          </span>
        </div>
      )}
      {subtitle && <p className="text-xs text-gray-500 mt-2">{subtitle}</p>}
    </div>
  )
}

