/** Analytics dashboard — usage over time, cost breakdown, provider comparison. */

import { useState } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { api } from '#/lib/api-client'
import { queryKeys } from '#/lib/query-keys'
import type { AnalyticsOverview, DailyCostStat, DailyUsageStat, ProviderStat } from '#/lib/types'
import { PageLayout } from '#/components/page-layout'
import { PageSkeleton } from '#/components/loading-skeleton'
import { UsageAreaChart } from '#/components/usage-area-chart'
import { CostBarChart } from '#/components/cost-bar-chart'
import { ProviderComparisonChart } from '#/components/provider-comparison-chart'
import { Briefcase, DollarSign, Target, FileText } from 'lucide-react'

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
      description="Usage metrics, cost tracking, and provider comparison"
      actions={
        <div className="flex items-center gap-1 rounded-lg bg-muted p-1">
          {(['7d', '30d', '90d'] as Period[]).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`rounded-md px-3 py-1.5 text-[12px] font-medium transition-colors cursor-pointer ${
                period === p
                  ? 'bg-card text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      }
    >
      {isLoading ? (
        <PageSkeleton />
      ) : (
        <div className="space-y-5 max-w-5xl">
          {/* Overview stat cards */}
          {overview && (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <AnalyticsStatCard label="Total Jobs" value={overview.total_jobs} icon={Briefcase} color="primary" />
              <AnalyticsStatCard label="Total Cost" value={`$${overview.total_cost_usd.toFixed(4)}`} icon={DollarSign} color="blue" />
              <AnalyticsStatCard
                label="Avg Confidence"
                value={overview.avg_confidence != null ? `${(overview.avg_confidence * 100).toFixed(1)}%` : '\u2014'}
                icon={Target}
                color="green"
              />
              <AnalyticsStatCard label="Active Schemas" value={overview.active_schemas} icon={FileText} color="purple" />
            </div>
          )}

          {/* Usage over time */}
          <section className="rounded-lg border border-border bg-card p-5">
            <h2 className="text-sm font-semibold text-foreground mb-4">Usage Over Time</h2>
            <UsageAreaChart data={usage} />
          </section>

          {/* Cost breakdown */}
          <section className="rounded-lg border border-border bg-card p-5">
            <h2 className="text-sm font-semibold text-foreground mb-4">Cost Breakdown by Provider</h2>
            <CostBarChart data={costs} />
          </section>

          {/* Provider comparison */}
          <section className="rounded-lg border border-border bg-card p-5">
            <h2 className="text-sm font-semibold text-foreground mb-4">Provider Comparison</h2>
            <ProviderComparisonChart data={providers} />
          </section>
        </div>
      )}
    </PageLayout>
  )
}

function AnalyticsStatCard({
  label,
  value,
  icon: Icon,
  color,
}: {
  label: string
  value: string | number
  icon: React.ElementType
  color: 'primary' | 'blue' | 'green' | 'purple'
}) {
  const colorMap = {
    primary: 'bg-primary/10 text-primary',
    blue: 'bg-blue-500/10 text-blue-600 dark:text-blue-400',
    green: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
    purple: 'bg-purple-500/10 text-purple-600 dark:text-purple-400',
  }
  return (
    <div className="rounded-lg border border-border bg-card p-4 flex items-start justify-between">
      <div>
        <p className="text-[12px] font-medium text-muted-foreground uppercase tracking-wide">{label}</p>
        <p className="text-2xl font-semibold text-foreground mt-1 tabular-nums">{value}</p>
      </div>
      <div className={`rounded-lg p-2.5 ${colorMap[color]}`}>
        <Icon size={18} strokeWidth={1.75} />
      </div>
    </div>
  )
}
