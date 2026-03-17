/** Stacked area chart: daily job volume by status (success / failed / review). */

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import type { DailyUsageStat } from '#/lib/types'

interface Props {
  data: DailyUsageStat[]
}

export function UsageAreaChart({ data }: Props) {
  if (data.length === 0) {
    return <p className="text-sm text-muted-foreground/70 py-8 text-center">No data for this period.</p>
  }
  return (
    <ResponsiveContainer width="100%" height={280}>
      <AreaChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="colorSuccess" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="colorFailed" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="colorReview" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border, #e4e4e7)" />
        <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={(v) => v.slice(5)} />
        <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
        <Tooltip
          contentStyle={{ fontSize: 12 }}
          formatter={(value: number, name: string) => [value, name]}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Area type="monotone" dataKey="success_count" name="Success" stroke="#22c55e" fill="url(#colorSuccess)" strokeWidth={2} />
        <Area type="monotone" dataKey="failed_count" name="Failed" stroke="#ef4444" fill="url(#colorFailed)" strokeWidth={2} />
        <Area type="monotone" dataKey="review_count" name="Review" stroke="#3b82f6" fill="url(#colorReview)" strokeWidth={2} />
      </AreaChart>
    </ResponsiveContainer>
  )
}
