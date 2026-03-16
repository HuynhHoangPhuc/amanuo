/** Horizontal bar chart: provider comparison by job count, success rate, and cost. */

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import type { ProviderStat } from '#/lib/types'

interface Props {
  data: ProviderStat[]
}

export function ProviderComparisonChart({ data }: Props) {
  if (data.length === 0) {
    return <p className="text-sm text-gray-400 py-8 text-center">No provider data for this period.</p>
  }

  const chartData = data.map((p) => ({
    provider: p.provider,
    'Jobs': p.job_count,
    'Success %': parseFloat(p.success_rate.toFixed(1)),
    'Cost ($)': parseFloat(p.total_cost_usd.toFixed(4)),
  }))

  return (
    <ResponsiveContainer width="100%" height={Math.max(200, data.length * 60)}>
      <BarChart
        layout="vertical"
        data={chartData}
        margin={{ top: 4, right: 16, left: 24, bottom: 0 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis type="number" tick={{ fontSize: 11 }} />
        <YAxis type="category" dataKey="provider" tick={{ fontSize: 11 }} width={56} />
        <Tooltip contentStyle={{ fontSize: 12 }} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey="Jobs" fill="#3b82f6" barSize={14} />
        <Bar dataKey="Success %" fill="#22c55e" barSize={14} />
        <Bar dataKey="Cost ($)" fill="#f59e0b" barSize={14} />
      </BarChart>
    </ResponsiveContainer>
  )
}
