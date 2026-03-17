/** Analytics dashboard — usage over time, cost breakdown, provider comparison. */

import { useState } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { TrendingUp } from 'lucide-react'
import { api } from '#/lib/api-client'
import { queryKeys } from '#/lib/query-keys'
import type { AnalyticsOverview, DailyCostStat, DailyUsageStat, ProviderStat } from '#/lib/types'
import { PageLayout } from '#/components/page-layout'
import { PageSkeleton } from '#/components/loading-skeleton'
import { UsageAreaChart } from '#/components/usage-area-chart'
import { CostBarChart } from '#/components/cost-bar-chart'
import { ProviderComparisonChart } from '#/components/provider-comparison-chart'

export const Route = createFileRoute('/analytics')({ component: AnalyticsDashboardPage })

type Period = '7d' | '30d' | '90d'

function AnalyticsDashboardPage() {
  const [period, setPeriod] = useState<Period>('30d')

  const { data: overview, isLoading: loadingOverview } = useQuery({
    queryKey: queryKeys.analytics.overview(period),
    queryFn: () => api.get<AnalyticsOverview>(`/analytics/overview?period=${period}`),
    refetchInterval: 60_000,
  })

  const { data: usage = [], isLoading: loadingUsage } = useQuery({
    queryKey: queryKeys.analytics.usage(period),
    queryFn: () => api.get<DailyUsageStat[]>(`/analytics/usage?period=${period}`),
    refetchInterval: 60_000,
  })

  const { data: costs = [], isLoading: loadingCosts } = useQuery({
    queryKey: queryKeys.analytics.costs(period),
    queryFn: () => api.get<DailyCostStat[]>(`/analytics/costs?period=${period}`),
    refetchInterval: 60_000,
  })

  const { data: providers = [], isLoading: loadingProviders } = useQuery({
    queryKey: queryKeys.analytics.providers(period),
    queryFn: () => api.get<ProviderStat[]>(`/analytics/providers?period=${period}`),
    refetchInterval: 60_000,
  })

  const isLoading = loadingOverview || loadingUsage || loadingCosts || loadingProviders

  return (
    <PageLayout
      title="Analytics"
      actions={
        <div className="flex items-center gap-2">
          <TrendingUp size={16} className="text-muted-foreground/70" />
          <div className="flex rounded-lg border border-border overflow-hidden">
            {(['7d', '30d', '90d'] as Period[]).map((p) => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={`px-3 py-1.5 text-xs font-medium transition-colors ${
                  period === p
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-card text-muted-foreground hover:bg-muted'
                }`}
              >
                {p}
              </button>
            ))}
          </div>
        </div>
      }
    >
      {isLoading ? (
        <PageSkeleton />
      ) : (
        <div className="space-y-6 max-w-5xl">
          {/* Overview stat cards */}
          {overview && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <StatCard label="Total Jobs" value={overview.total_jobs} />
              <StatCard label="Total Cost" value={`$${overview.total_cost_usd.toFixed(4)}`} color="blue" />
              <StatCard
                label="Avg Confidence"
                value={overview.avg_confidence != null ? `${(overview.avg_confidence * 100).toFixed(1)}%` : '—'}
                color="green"
              />
              <StatCard label="Active Schemas" value={overview.active_schemas} color="purple" />
            </div>
          )}

          {/* Usage over time */}
          <section className="rounded-xl border border-border bg-card p-5">
            <h2 className="text-sm font-semibold text-foreground mb-4">Usage Over Time</h2>
            <UsageAreaChart data={usage} />
          </section>

          {/* Cost breakdown */}
          <section className="rounded-xl border border-border bg-card p-5">
            <h2 className="text-sm font-semibold text-foreground mb-4">Cost Breakdown by Provider</h2>
            <CostBarChart data={costs} />
          </section>

          {/* Provider comparison */}
          <section className="rounded-xl border border-border bg-card p-5">
            <h2 className="text-sm font-semibold text-foreground mb-4">Provider Comparison</h2>
            <ProviderComparisonChart data={providers} />
          </section>
        </div>
      )}
    </PageLayout>
  )
}

function StatCard({
  label,
  value,
  color = 'gray',
}: {
  label: string
  value: string | number
  color?: 'gray' | 'blue' | 'green' | 'purple'
}) {
  const colorMap = {
    gray: 'bg-muted text-foreground',
    blue: 'bg-primary/10 text-primary',
    green: 'bg-green-500/10 text-green-700',
    purple: 'bg-purple-500/10 text-purple-700',
  }
  return (
    <div className={`rounded-xl border border-border p-4 ${colorMap[color]}`}>
      <p className="text-xs font-medium opacity-70">{label}</p>
      <p className="text-2xl font-bold mt-1">{value}</p>
    </div>
  )
}
