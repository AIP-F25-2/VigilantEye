import { Circle, CheckCircle, Activity, Check, Lock, AlertCircle } from 'lucide-react'
import { cn } from '@/utils/cn'

interface TicketStatusBadgeProps {
  status: string
}

export function TicketStatusBadge({ status }: TicketStatusBadgeProps) {
  const statusConfig = {
    open: {
      text: 'Open',
      icon: Circle,
      classes: 'bg-blue-100 text-blue-800',
    },
    acknowledged: {
      text: 'Acknowledged',
      icon: CheckCircle,
      classes: 'bg-yellow-100 text-yellow-800',
    },
    in_progress: {
      text: 'In Progress',
      icon: Activity,
      classes: 'bg-purple-100 text-purple-800',
    },
    resolved: {
      text: 'Resolved',
      icon: Check,
      classes: 'bg-green-100 text-green-800',
    },
    closed: {
      text: 'Closed',
      icon: Lock,
      classes: 'bg-gray-100 text-gray-800',
    },
  }

  const config = statusConfig[status.toLowerCase() as keyof typeof statusConfig] || {
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
      <Icon className="w-3 h-3 mr-1" />
      {config.text}
    </span>
  )
}

