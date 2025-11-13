import { useState, useEffect } from 'react'
import { Calendar, X } from 'lucide-react'
import { subDays } from 'date-fns'
import toast from 'react-hot-toast'
import { Button } from '@/components/Button'
import type { DateRange } from '@/types/analytics'

interface DateRangeSelectorProps {
  value: DateRange | null
  onChange: (range: DateRange | null) => void
  presets?: Array<{ label: string; value: DateRange | null }>
}

const defaultPresets = [
  { label: 'Last 24h', value: { from: subDays(new Date(), 1), to: new Date() } },
  { label: 'Last 7d', value: { from: subDays(new Date(), 7), to: new Date() } },
  { label: 'Last 30d', value: { from: subDays(new Date(), 30), to: new Date() } },
  { label: 'All Time', value: null },
]

export function DateRangeSelector({
  value,
  onChange,
  presets = defaultPresets,
}: DateRangeSelectorProps) {
  const [selectedPreset, setSelectedPreset] = useState<string | null>(null)
  const [customFrom, setCustomFrom] = useState('')
  const [customTo, setCustomTo] = useState('')
  const [isCustomMode, setIsCustomMode] = useState(false)

  // Sync state when value prop changes
  useEffect(() => {
    if (!value) {
      setSelectedPreset(null)
      setCustomFrom('')
      setCustomTo('')
      setIsCustomMode(false)
      return
    }

    // Check if value matches a preset
    const matchingPreset = presets.find((preset) => {
      if (!preset.value) return false
      const presetFrom = typeof preset.value.from === 'string' ? new Date(preset.value.from) : preset.value.from
      const presetTo = typeof preset.value.to === 'string' ? new Date(preset.value.to) : preset.value.to
      const valueFrom = typeof value.from === 'string' ? new Date(value.from) : value.from
      const valueTo = typeof value.to === 'string' ? new Date(value.to) : value.to

      return (
        presetFrom.getTime() === valueFrom.getTime() && presetTo.getTime() === valueTo.getTime()
      )
    })

    if (matchingPreset) {
      setSelectedPreset(matchingPreset.label)
      setIsCustomMode(false)
    } else {
      setIsCustomMode(true)
      setCustomFrom(typeof value.from === 'string' ? value.from : value.from.toISOString().split('T')[0])
      setCustomTo(typeof value.to === 'string' ? value.to : value.to.toISOString().split('T')[0])
    }
  }, [value, presets])

  const handlePresetClick = (preset: { label: string; value: DateRange | null }) => {
    setSelectedPreset(preset.label)
    onChange(preset.value)
    setIsCustomMode(false)
  }

  const handleApplyCustomRange = () => {
    if (!customFrom || !customTo) {
      toast.error('Please select both start and end dates')
      return
    }

    const fromDate = new Date(customFrom)
    const toDate = new Date(customTo)

    if (fromDate > toDate) {
      toast.error('Invalid date range: start date must be before end date')
      return
    }

    onChange({ from: customFrom, to: customTo })
    setSelectedPreset(null)
  }

  const handleClear = () => {
    onChange(null)
    setSelectedPreset(null)
    setIsCustomMode(false)
    setCustomFrom('')
    setCustomTo('')
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      {/* Preset Buttons */}
      <div className="flex flex-wrap gap-2">
        {presets.map((preset) => (
          <button
            key={preset.label}
            onClick={() => handlePresetClick(preset)}
            className={`px-3 py-1.5 text-sm font-medium rounded-full transition-colors ${
              selectedPreset === preset.label
                ? 'bg-primary-600 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            {preset.label}
          </button>
        ))}
      </div>

      {/* Custom Range Toggle */}
      <Button
        onClick={() => setIsCustomMode(!isCustomMode)}
        variant={isCustomMode ? 'primary' : 'secondary'}
        size="sm"
      >
        <Calendar className="w-4 h-4 mr-2" />
        Custom Range
      </Button>

      {/* Custom Range Inputs */}
      {isCustomMode && (
        <div className="flex items-center gap-2">
          <input
            type="date"
            value={customFrom}
            onChange={(e) => setCustomFrom(e.target.value)}
            className="px-3 py-1.5 text-sm rounded-md border-gray-300 focus:border-primary-500 focus:ring-primary-500 border"
          />
          <span className="text-gray-500">to</span>
          <input
            type="date"
            value={customTo}
            onChange={(e) => setCustomTo(e.target.value)}
            className="px-3 py-1.5 text-sm rounded-md border-gray-300 focus:border-primary-500 focus:ring-primary-500 border"
          />
          <Button onClick={handleApplyCustomRange} variant="primary" size="sm">
            Apply
          </Button>
        </div>
      )}

      {/* Clear Button */}
      {value && (
        <Button onClick={handleClear} variant="ghost" size="sm">
          <X className="w-4 h-4 mr-1" />
          Clear
        </Button>
      )}
    </div>
  )
}

