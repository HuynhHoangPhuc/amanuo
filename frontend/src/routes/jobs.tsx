/** Jobs list with status filter tabs. */

import { useState } from 'react'
import { createFileRoute, Link } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { api } from '#/lib/api-client'
import { queryKeys } from '#/lib/query-keys'
import type { JobListResponse, JobStatus } from '#/lib/types'
import { PageLayout } from '#/components/page-layout'
import { StatusBadge } from '#/components/status-badge'
import { TableRowSkeleton } from '#/components/loading-skeleton'
import { Briefcase } from 'lucide-react'

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
    <PageLayout title="Jobs" description="View and manage extraction jobs">
      {/* Filter tabs */}
      <div className="mb-4 flex items-center gap-1 rounded-lg bg-muted p-1 w-fit">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => setStatusFilter(f.value)}
            className={`rounded-md px-3 py-1.5 text-[12px] font-medium transition-colors cursor-pointer ${
              statusFilter === f.value
                ? 'bg-card text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      <div className="rounded-lg border border-border bg-card">
        <div className="overflow-x-auto">
          <table className="w-full text-[13px]">
            <thead>
              <tr className="border-b border-border">
                <th className="px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Job ID</th>
                <th className="px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Status</th>
                <th className="px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Mode</th>
                <th className="px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Confidence</th>
                <th className="px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Created</th>
              </tr>
            </thead>
            <tbody>
              {isLoading &&
                Array.from({ length: 5 }).map((_, i) => (
                  <TableRowSkeleton key={i} cols={5} />
                ))}
              {!isLoading &&
                jobs.map((job) => (
                  <tr key={job.id} className="border-b border-border/50 hover:bg-accent/50 transition-colors">
                    <td className="px-4 py-2.5">
                      <Link
                        to="/jobs/$jobId"
                        params={{ jobId: job.id }}
                        className="font-mono text-[12px] text-primary hover:underline"
                      >
                        {job.id.slice(0, 12)}...
                      </Link>
                    </td>
                    <td className="px-4 py-2.5">
                      <StatusBadge status={job.status as JobStatus} />
                    </td>
                    <td className="px-4 py-2.5 text-muted-foreground capitalize">{job.mode}</td>
                    <td className="px-4 py-2.5 text-muted-foreground tabular-nums">
                      {job.confidence != null
                        ? `${Math.round(job.confidence * 100)}%`
                        : '\u2014'}
                    </td>
                    <td className="px-4 py-2.5 text-[12px] text-muted-foreground tabular-nums">
                      {new Date(job.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              {!isLoading && jobs.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-12 text-center text-muted-foreground">
                    <div className="flex flex-col items-center gap-2">
                      <Briefcase size={24} className="text-muted-foreground/40" />
                      <p className="text-[13px]">No jobs found.</p>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </PageLayout>
  )
}
