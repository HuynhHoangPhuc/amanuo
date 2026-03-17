/** Jobs list with status filter. */

import { useState } from 'react'
import { createFileRoute, Link } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { api } from '#/lib/api-client'
import { queryKeys } from '#/lib/query-keys'
import type { JobListResponse, JobStatus } from '#/lib/types'
import { PageLayout } from '#/components/page-layout'
import { StatusBadge } from '#/components/status-badge'
import { TableRowSkeleton } from '#/components/loading-skeleton'

export const Route = createFileRoute('/jobs')({ component: JobsPage })

const STATUS_FILTERS: Array<{ label: string; value: string }> = [
  { label: 'All', value: '' },
  { label: 'Pending', value: 'pending' },
  { label: 'Processing', value: 'processing' },
  { label: 'Completed', value: 'completed' },
  { label: 'Failed', value: 'failed' },
]

function JobsPage() {
  const [statusFilter, setStatusFilter] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.jobs.list(statusFilter),
    queryFn: () => {
      const qs = statusFilter ? `?status=${statusFilter}` : ''
      return api.get<JobListResponse>(`/jobs${qs}`)
    },
  })

  const jobs = data?.jobs ?? []

  return (
    <PageLayout title="Jobs">
      <div className="mb-4 flex gap-2">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => setStatusFilter(f.value)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              statusFilter === f.value
                ? 'bg-primary text-primary-foreground'
                : 'bg-card border border-border text-muted-foreground hover:bg-muted'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      <div className="rounded-xl border border-border bg-card">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border/50 text-xs text-muted-foreground">
              <th className="px-5 py-3 text-left font-medium">Job ID</th>
              <th className="px-5 py-3 text-left font-medium">Status</th>
              <th className="px-5 py-3 text-left font-medium">Mode</th>
              <th className="px-5 py-3 text-left font-medium">Confidence</th>
              <th className="px-5 py-3 text-left font-medium">Created</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/50">
            {isLoading &&
              Array.from({ length: 5 }).map((_, i) => (
                <TableRowSkeleton key={i} cols={5} />
              ))}
            {!isLoading &&
              jobs.map((job) => (
                <tr key={job.id} className="hover:bg-muted">
                  <td className="px-5 py-3">
                    <Link
                      to="/jobs/$jobId"
                      params={{ jobId: job.id }}
                      className="font-mono text-xs text-primary hover:underline"
                    >
                      {job.id.slice(0, 12)}…
                    </Link>
                  </td>
                  <td className="px-5 py-3">
                    <StatusBadge status={job.status as JobStatus} />
                  </td>
                  <td className="px-5 py-3 text-muted-foreground">{job.mode}</td>
                  <td className="px-5 py-3 text-muted-foreground">
                    {job.confidence != null
                      ? `${Math.round(job.confidence * 100)}%`
                      : '—'}
                  </td>
                  <td className="px-5 py-3 text-xs text-muted-foreground">
                    {new Date(job.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            {!isLoading && jobs.length === 0 && (
              <tr>
                <td colSpan={5} className="px-5 py-8 text-center text-muted-foreground/70">
                  No jobs found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </PageLayout>
  )
}
