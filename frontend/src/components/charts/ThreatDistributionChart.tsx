import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'

interface ThreatDistributionChartProps {
  data: Array<{
    threat_level: string
    count: number
    percentage: number
  }>
  isLoading?: boolean
  height?: number
}

const COLORS: Record<string, string> = {
  low: '#9ca3af',
  medium: '#fbbf24',
  high: '#f97316',
  critical: '#ef4444',
}

export function ThreatDistributionChart({
  data,
  isLoading = false,
  height = 300,
}: ThreatDistributionChartProps) {
  if (isLoading) {
    return (
      <div className="animate-pulse bg-gray-200 rounded" style={{ height }} />
    )
  }

  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center text-gray-500" style={{ height }}>
        No threat data available
      </div>
    )
  }

  const chartData = data.map((d) => ({
    name: d.threat_level.toUpperCase(),
    value: d.count,
    percentage: d.percentage,
    fill: COLORS[d.threat_level.toLowerCase()] || '#9ca3af',
  }))

  const totalTickets = data.reduce((sum, d) => sum + d.count, 0)

  const renderCustomLabel = ({
    cx,
    cy,
    midAngle,
    innerRadius,
    outerRadius,
    percent,
  }: any) => {
    const RADIAN = Math.PI / 180
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5
    const x = cx + radius * Math.cos(-midAngle * RADIAN)
    const y = cy + radius * Math.sin(-midAngle * RADIAN)

    return (
      <text
        x={x}
        y={y}
        fill="white"
        textAnchor={x > cx ? 'start' : 'end'}
        dominantBaseline="central"
        fontSize={12}
        fontWeight="bold"
      >
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Pie
          data={chartData}
          cx="50%"
          cy="50%"
          labelLine={false}
          label={renderCustomLabel}
          outerRadius={80}
          fill="#8884d8"
          dataKey="value"
        >
          {chartData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.fill} />
          ))}
        </Pie>
        <Tooltip
          formatter={(value: number, name: string) => {
            const entry = chartData.find((d) => d.name === name)
            return [`${value} tickets (${entry?.percentage.toFixed(1)}%)`, name]
          }}
        />
        <Legend verticalAlign="bottom" height={36} />
        <text
          x="50%"
          y="50%"
          textAnchor="middle"
          dominantBaseline="middle"
          fontSize={16}
          fontWeight="bold"
          fill="#374151"
        >
          {totalTickets}
        </text>
      </PieChart>
    </ResponsiveContainer>
  )
}

