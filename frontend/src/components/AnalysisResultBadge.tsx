import { Clock, CheckCircle, AlertTriangle } from 'lucide-react'
import { cn } from '@/utils/cn'

interface AnalysisResultBadgeProps {
  result: 'clean' | 'suspicious' | null
}

export function AnalysisResultBadge({ result }: AnalysisResultBadgeProps) {
  if (result === null) {
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
        <Clock className="w-3 h-3 mr-1" />
        Pending
      </span>
    )
  }

  if (result === 'clean') {
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
        <CheckCircle className="w-3 h-3 mr-1" />
        Clean
      </span>
    )
  }

  return (
    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
      <AlertTriangle className="w-3 h-3 mr-1" />
      Suspicious
    </span>
  )
}

