/** Stacked bar chart: daily cost breakdown by provider. */

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
import type { DailyCostStat } from '#/lib/types'

interface Props {
  data: DailyCostStat[]
}

// Stable provider → color mapping
const PROVIDER_COLORS: Record<string, string> = {
  gemini: '#6366f1',
  mistral: '#8b5cf6',
  local: '#10b981',
  unknown: '#a1a1aa',
}

function colorForProvider(provider: string): string {
  return PROVIDER_COLORS[provider] ?? '#94a3b8'
}

function buildChartData(data: DailyCostStat[]) {
  // Collect all provider keys seen across all days
  const allProviders = new Set<string>()
  for (const d of data) {
    Object.keys(d.provider_breakdown).forEach((p) => allProviders.add(p))
  }
  return {
    rows: data.map((d) => ({
      date: d.date,
      ...Object.fromEntries(
        Array.from(allProviders).map((p) => [p, d.provider_breakdown[p] ?? 0]),
      ),
    })),
    providers: Array.from(allProviders),
  }
}

export function CostBarChart({ data }: Props) {
  if (data.length === 0) {
    return <p className="text-sm text-muted-foreground/70 py-8 text-center">No cost data for this period.</p>
  }
  const { rows, providers } = buildChartData(data)
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={rows} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border, #e4e4e7)" />
        <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={(v) => v.slice(5)} />
        <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `$${v.toFixed(3)}`} />
        <Tooltip
          contentStyle={{ fontSize: 12 }}
          formatter={(value: number, name: string) => [`$${value.toFixed(4)}`, name]}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {providers.map((p) => (
          <Bar key={p} dataKey={p} stackId="cost" fill={colorForProvider(p)} name={p} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  )
}
