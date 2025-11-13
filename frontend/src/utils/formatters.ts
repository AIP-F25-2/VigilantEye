import { format, formatDistanceToNow } from 'date-fns'

export function formatBytes(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`
  }
  if (bytes < 1024 * 1024 * 1024) {
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
}

export function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${seconds}s`
  }
  if (seconds < 3600) {
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return remainingSeconds > 0 ? `${minutes}m ${remainingSeconds}s` : `${minutes}m`
  }
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`
}

export function formatDate(dateString: string, formatStr: string = 'PPpp'): string {
  const date = new Date(dateString)
  return format(date, formatStr)
}

export function formatRelativeTime(dateString: string): string {
  return formatDistanceToNow(new Date(dateString), { addSuffix: true })
}

export function truncateFilename(filename: string, maxLength: number = 30): string {
  if (filename.length <= maxLength) {
    return filename
  }

  // Try to preserve extension
  const lastDotIndex = filename.lastIndexOf('.')
  if (lastDotIndex > 0 && lastDotIndex < filename.length - 1) {
    const extension = filename.substring(lastDotIndex)
    const name = filename.substring(0, lastDotIndex)
    if (name.length + extension.length + 3 <= maxLength) {
      return `${name.substring(0, maxLength - extension.length - 3)}...${extension}`
    }
  }

  return `${filename.substring(0, maxLength - 3)}...`
}

export function formatLatency(milliseconds: number): string {
  if (milliseconds < 1) {
    return `${(milliseconds * 1000).toFixed(0)} μs`
  }
  if (milliseconds < 1000) {
    return `${milliseconds.toFixed(0)} ms`
  }
  if (milliseconds < 60000) {
    return `${(milliseconds / 1000).toFixed(2)} s`
  }
  return `${(milliseconds / 60000).toFixed(2)} min`
}

export function formatPercentage(value: number, decimals: number = 1): string {
  return `${value.toFixed(decimals)}%`
}

