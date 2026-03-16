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
import { BarChart3 } from 'lucide-react'

export const Route = createFileRoute('/accuracy')({ component: AccuracyDashboardPage })

function AccuracyDashboardPage() {
  const [selectedSchema, setSelectedSchema] = useState<string>('')

  // Fetch available schemas
  const { data: schemasData } = useQuery({
    queryKey: queryKeys.schemas.list(),
    queryFn: () => api.get<{ schemas: SchemaResponse[]; total: number }>('/schemas'),
  })

  // Fetch accuracy history for selected schema
  const { data: metrics, isLoading: loadingMetrics } = useQuery({
    queryKey: queryKeys.accuracy.schema(selectedSchema),
    queryFn: () => api.get<AccuracyMetric[]>(`/accuracy/${selectedSchema}`),
    enabled: !!selectedSchema,
  })

  // Fetch field-level breakdown
  const { data: fieldData, isLoading: loadingFields } = useQuery({
    queryKey: queryKeys.accuracy.fields(selectedSchema),
    queryFn: () => api.get<AccuracyMetric>(`/accuracy/${selectedSchema}/fields`),
    enabled: !!selectedSchema,
  })

  const schemas = schemasData?.schemas ?? []

  // Auto-select first schema via effect (avoid setState during render)
  const firstSchemaId = schemas[0]?.id
  useEffect(() => {
    if (!selectedSchema && firstSchemaId) {
      setSelectedSchema(firstSchemaId)
    }
  }, [firstSchemaId, selectedSchema])

  return (
    <PageLayout
      title="Accuracy Dashboard"
      actions={
        <div className="flex items-center gap-2">
          <BarChart3 size={16} className="text-gray-400" />
          <select
            value={selectedSchema}
            onChange={(e) => setSelectedSchema(e.target.value)}
            className="rounded-lg border border-gray-200 px-3 py-1.5 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-400"
          >
            <option value="" disabled>Select schema...</option>
            {schemas.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
        </div>
      }
    >
      {!selectedSchema ? (
        <p className="text-sm text-gray-400 py-8">Select a schema to view accuracy metrics.</p>
      ) : loadingMetrics || loadingFields ? (
        <PageSkeleton />
      ) : (
        <div className="space-y-6 max-w-4xl">
          {/* Overview stats */}
          {fieldData && (
            <div className="grid grid-cols-4 gap-4">
              <StatCard label="Total Reviews" value={fieldData.total_reviews} />
              <StatCard label="Approved" value={fieldData.approved_count} color="green" />
              <StatCard label="Corrected" value={fieldData.corrected_count} color="blue" />
              <StatCard
                label="Accuracy"
                value={`${fieldData.accuracy_pct.toFixed(1)}%`}
                color={fieldData.accuracy_pct >= 90 ? 'green' : fieldData.accuracy_pct >= 70 ? 'yellow' : 'red'}
              />
            </div>
          )}

          {/* Accuracy trend chart */}
          <section className="rounded-xl border border-gray-200 bg-white p-5">
            <h2 className="text-sm font-semibold text-gray-700 mb-4">Accuracy Over Time</h2>
            <AccuracyChart metrics={metrics ?? []} />
          </section>

          {/* Field-level breakdown */}
          <section>
            <h2 className="text-sm font-semibold text-gray-700 mb-3">Field-Level Accuracy</h2>
            <FieldAccuracyTable fieldAccuracy={fieldData?.field_accuracy ?? {}} />
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
  color?: 'gray' | 'green' | 'blue' | 'yellow' | 'red'
}) {
  const colorMap = {
    gray: 'bg-gray-50 text-gray-700',
    green: 'bg-green-50 text-green-700',
    blue: 'bg-blue-50 text-blue-700',
    yellow: 'bg-yellow-50 text-yellow-700',
    red: 'bg-red-50 text-red-700',
  }
  return (
    <div className={`rounded-xl border border-gray-200 p-4 ${colorMap[color]}`}>
      <p className="text-xs font-medium opacity-70">{label}</p>
      <p className="text-2xl font-bold mt-1">{value}</p>
    </div>
  )
}
