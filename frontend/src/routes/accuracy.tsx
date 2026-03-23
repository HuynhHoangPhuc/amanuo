/** Accuracy dashboard — per-schema accuracy trends and field-level breakdown. */

import { useState, useEffect } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { api } from '#/lib/api-client'
import { queryKeys } from '#/lib/query-keys'
import type { AccuracyMetric, SchemaResponse } from '#/lib/types'
import { PageLayout } from '#/components/page-layout'
import { AccuracyChart } from '#/components/accuracy-chart'
import { FieldAccuracyTable } from '#/components/field-accuracy-table'
import { PageSkeleton } from '#/components/loading-skeleton'
import { BarChart3, FileCheck, FileX, Target, Hash } from 'lucide-react'

export const Route = createFileRoute('/accuracy')({ component: AccuracyDashboardPage })

function AccuracyDashboardPage() {
  const [selectedSchema, setSelectedSchema] = useState<string>('')

  const { data: schemasData } = useQuery({
    queryKey: queryKeys.schemas.list(),
    queryFn: () => api.get<{ schemas: SchemaResponse[]; total: number }>('/schemas'),
  })

  const { data: metrics, isLoading: loadingMetrics } = useQuery({
    queryKey: queryKeys.accuracy.schema(selectedSchema),
    queryFn: () => api.get<AccuracyMetric[]>(`/accuracy/${selectedSchema}`),
    enabled: !!selectedSchema,
  })

  const { data: fieldData, isLoading: loadingFields } = useQuery({
    queryKey: queryKeys.accuracy.fields(selectedSchema),
    queryFn: () => api.get<AccuracyMetric>(`/accuracy/${selectedSchema}/fields`),
    enabled: !!selectedSchema,
  })

  const schemas = schemasData?.schemas ?? []

  const firstSchemaId = schemas[0]?.id
  useEffect(() => {
    if (!selectedSchema && firstSchemaId) {
      setSelectedSchema(firstSchemaId)
    }
  }, [firstSchemaId, selectedSchema])

  return (
    <PageLayout
      title="Accuracy"
      description="Per-schema accuracy trends and field-level breakdown"
      actions={
        <select
          value={selectedSchema}
          onChange={(e) => setSelectedSchema(e.target.value)}
          className="rounded-md border border-input bg-transparent px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring cursor-pointer"
        >
          <option value="" disabled>Select schema...</option>
          {schemas.map((s) => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>
      }
    >
      {!selectedSchema ? (
        <div className="rounded-lg border border-border bg-card py-12 text-center text-muted-foreground">
          <div className="flex flex-col items-center gap-2">
            <BarChart3 size={24} className="text-muted-foreground/40" />
            <p className="text-[13px]">Select a schema to view accuracy metrics.</p>
          </div>
        </div>
      ) : loadingMetrics || loadingFields ? (
        <PageSkeleton />
      ) : (
        <div className="space-y-5 max-w-4xl">
          {/* Overview stats */}
          {fieldData && (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <AccuracyStatCard label="Total Reviews" value={fieldData.total_reviews} icon={Hash} color="primary" />
              <AccuracyStatCard label="Approved" value={fieldData.approved_count} icon={FileCheck} color="green" />
              <AccuracyStatCard label="Corrected" value={fieldData.corrected_count} icon={FileX} color="blue" />
              <AccuracyStatCard
                label="Accuracy"
                value={`${fieldData.accuracy_pct.toFixed(1)}%`}
                icon={Target}
                color={fieldData.accuracy_pct >= 90 ? 'green' : fieldData.accuracy_pct >= 70 ? 'yellow' : 'red'}
              />
            </div>
          )}

          {/* Accuracy trend chart */}
          <section className="rounded-lg border border-border bg-card p-5">
            <h2 className="text-sm font-semibold text-foreground mb-4">Accuracy Over Time</h2>
            <AccuracyChart metrics={metrics ?? []} />
          </section>

          {/* Field-level breakdown */}
          <section>
            <h2 className="text-sm font-semibold text-foreground mb-3">Field-Level Accuracy</h2>
            <FieldAccuracyTable fieldAccuracy={fieldData?.field_accuracy ?? {}} />
          </section>
        </div>
      )}
    </PageLayout>
  )
}

function AccuracyStatCard({
  label,
  value,
  icon: Icon,
  color,
}: {
  label: string
  value: string | number
  icon: React.ElementType
  color: 'primary' | 'green' | 'blue' | 'yellow' | 'red'
}) {
  const colorMap = {
    primary: 'bg-primary/10 text-primary',
    green: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
    blue: 'bg-blue-500/10 text-blue-600 dark:text-blue-400',
    yellow: 'bg-amber-500/10 text-amber-600 dark:text-amber-400',
    red: 'bg-red-500/10 text-red-600 dark:text-red-400',
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
