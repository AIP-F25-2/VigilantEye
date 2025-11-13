import {
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { formatLatency } from '@/utils/formatters'

interface ResponseTimeChartProps {
  data: {
    p50: number
    p95: number
    p99: number
  } | undefined
  isLoading?: boolean
  height?: number
}

export function ResponseTimeChart({
  data,
  isLoading = false,
  height = 300,
}: ResponseTimeChartProps) {
  if (isLoading) {
    return (
      <div className="animate-pulse bg-gray-200 rounded" style={{ height }} />
    )
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center text-gray-500" style={{ height }}>
        No response time data
      </div>
    )
  }

  const chartData = [
    { name: 'p50 (Median)', value: data.p50, fill: '#22c55e' },
    { name: 'p95', value: data.p95, fill: '#fbbf24' },
    { name: 'p99', value: data.p99, fill: '#ef4444' },
  ]

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="name" tick={{ fontSize: 12 }} />
        <YAxis
          tick={{ fontSize: 12 }}
          label={{ value: 'Time (ms)', angle: -90, position: 'insideLeft' }}
        />
        <Tooltip formatter={(value: number) => [formatLatency(value), 'Time']} />
        <Bar dataKey="value" radius={[8, 8, 0, 0]}>
          {chartData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.fill} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

