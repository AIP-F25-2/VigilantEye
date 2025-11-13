import { Info, AlertCircle, AlertTriangle, AlertOctagon } from 'lucide-react'
import { cn } from '@/utils/cn'

interface PriorityBadgeProps {
  priority: string
}

export function PriorityBadge({ priority }: PriorityBadgeProps) {
  const priorityConfig = {
    low: {
      text: 'Low',
      icon: Info,
      classes: 'bg-gray-100 text-gray-800',
    },
    medium: {
      text: 'Medium',
      icon: AlertCircle,
      classes: 'bg-yellow-100 text-yellow-800',
    },
    high: {
      text: 'High',
      icon: AlertTriangle,
      classes: 'bg-orange-100 text-orange-800',
    },
    critical: {
      text: 'Critical',
      icon: AlertOctagon,
      classes: 'bg-red-100 text-red-800',
    },
  }

  const config = priorityConfig[priority.toLowerCase() as keyof typeof priorityConfig] || {
    text: priority,
    icon: Info,
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
      <Icon className="w-3 h-3 mr-1" />
      {config.text}
    </span>
  )
}

