import { Upload, Loader2, CheckCircle, BarChart3, AlertCircle } from 'lucide-react'
import { cn } from '@/utils/cn'

interface VideoStatusBadgeProps {
  status: string
}

export function VideoStatusBadge({ status }: VideoStatusBadgeProps) {
  const statusConfig = {
    uploading: {
      text: 'Uploading',
      icon: Upload,
      classes: 'bg-blue-100 text-blue-800',
    },
    processing: {
      text: 'Processing',
      icon: Loader2,
      classes: 'bg-blue-100 text-blue-800',
    },
    ready: {
      text: 'Ready',
      icon: CheckCircle,
      classes: 'bg-green-100 text-green-800',
    },
    analyzing: {
      text: 'Analyzing',
      icon: BarChart3,
      classes: 'bg-yellow-100 text-yellow-800',
    },
    analyzed: {
      text: 'Analyzed',
      icon: CheckCircle,
      classes: 'bg-green-100 text-green-800',
    },
    error: {
      text: 'Error',
      icon: AlertCircle,
      classes: 'bg-red-100 text-red-800',
    },
  }

  const config = statusConfig[status as keyof typeof statusConfig] || {
    text: status,
    icon: AlertCircle,
    classes: 'bg-gray-100 text-gray-800',
  }

  const Icon = config.icon

  return (
    <span
      className={cn(
        'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
        config.classes
      )}
    >
      <Icon
        className={cn('w-3 h-3 mr-1', status === 'processing' || status === 'analyzing' ? 'animate-spin' : '')}
      />
      {config.text}
    </span>
  )
}

