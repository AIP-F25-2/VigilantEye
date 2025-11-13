import { useState, useEffect } from 'react'
import { differenceInSeconds } from 'date-fns'
import { Clock } from 'lucide-react'
import { cn } from '@/utils/cn'

interface TTLCountdownProps {
  expiresAt: string
}

function formatTimeRemaining(seconds: number): string {
  if (seconds <= 0) {
    return 'Expired'
  }

  if (seconds < 60) {
    return `${seconds}s`
  }

  if (seconds < 3600) {
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return remainingSeconds > 0 ? `${minutes}m ${remainingSeconds}s` : `${minutes}m`
  }

  if (seconds < 86400) {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`
  }

  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  return hours > 0 ? `${days}d ${hours}h` : `${days}d`
}

export function TTLCountdown({ expiresAt }: TTLCountdownProps) {
  const [timeRemaining, setTimeRemaining] = useState<number>(0)
  const [isExpired, setIsExpired] = useState(false)

  useEffect(() => {
    const updateCountdown = () => {
      const now = new Date()
      const expires = new Date(expiresAt)
      const remaining = differenceInSeconds(expires, now)

      setTimeRemaining(Math.max(0, remaining))
      setIsExpired(remaining <= 0)
    }

    // Update immediately
    updateCountdown()

    // Update every second
    const interval = setInterval(updateCountdown, 1000)

    return () => {
      clearInterval(interval)
    }
  }, [expiresAt])

  const formattedTime = formatTimeRemaining(timeRemaining)

  // Determine color based on time remaining
  let colorClass = 'text-green-600'
  if (isExpired || timeRemaining <= 0) {
    colorClass = 'text-gray-500'
  } else if (timeRemaining < 600) {
    // Less than 10 minutes
    colorClass = 'text-red-600'
  } else if (timeRemaining < 1800) {
    // Less than 30 minutes
    colorClass = 'text-yellow-600'
  }

  return (
    <span className={cn('inline-flex items-center text-sm font-medium', colorClass)}>
      <Clock className="w-4 h-4 mr-1" />
      {formattedTime}
    </span>
  )
}

