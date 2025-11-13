import { format, parseISO } from 'date-fns'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'

interface TicketsOverTimeChartProps {
  data: Array<{
    timestamp: string
    count: number
  }>
  isLoading?: boolean
  height?: number
}

export function TicketsOverTimeChart({
  data,
  isLoading = false,
  height = 300,
}: TicketsOverTimeChartProps) {
  if (isLoading) {
    return (
      <div className="animate-pulse bg-gray-200 rounded" style={{ height }} />
    )
  }

  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center text-gray-500" style={{ height }}>
        No data available
      </div>
    )
  }

  const chartData = data.map((d) => ({
    name: format(parseISO(d.timestamp), 'MMM dd HH:mm'),
    count: d.count,
  }))

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis
          dataKey="name"
          tick={{ fontSize: 12 }}
          angle={-45}
          textAnchor="end"
          height={80}
        />
        <YAxis tick={{ fontSize: 12 }} label={{ value: 'Tickets', angle: -90, position: 'insideLeft' }} />
        <Tooltip
          contentStyle={{
            backgroundColor: '#fff',
            border: '1px solid #e5e7eb',
            borderRadius: '0.375rem',
          }}
        />
        <Legend />
        <Line
          type="monotone"
          dataKey="count"
          stroke="#0ea5e9"
          strokeWidth={2}
          dot={{ fill: '#0ea5e9', r: 4 }}
          activeDot={{ r: 6 }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}

