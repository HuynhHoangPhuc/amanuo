/** Dashboard: job stats overview and recent activity. */

import { createFileRoute, Link } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { api } from '#/lib/api-client'
import { queryKeys } from '#/lib/query-keys'
import type { JobListResponse } from '#/lib/types'
import { PageLayout } from '#/components/page-layout'
import { StatusBadge } from '#/components/status-badge'
import { CardSkeleton } from '#/components/loading-skeleton'
import { Briefcase, CheckCircle, Clock, XCircle } from 'lucide-react'

export const Route = createFileRoute('/')({ component: DashboardPage })

function StatCard({
  label,
  value,
  icon: Icon,
}: {
  label: string
  value: number
  icon: React.ElementType
}) {
  return (
    <div className="rounded-md border border-border bg-card px-4 py-3 flex items-center gap-3">
      <Icon size={16} className="text-muted-foreground" />
      <div>
        <p className="text-xl font-semibold text-foreground tabular-nums">{value}</p>
        <p className="text-[11px] text-muted-foreground">{label}</p>
      </div>
    </div>
  )
}

function DashboardPage() {
  const { data, isLoading } = useQuery({
    queryKey: queryKeys.jobs.list(),
    queryFn: () => api.get<JobListResponse>('/jobs?limit=20'),
  })

  const jobs = data?.jobs ?? []
  const stats = {
    total: data?.total ?? 0,
    completed: jobs.filter((j) => j.status === 'completed').length,
    pending: jobs.filter((j) => j.status === 'pending' || j.status === 'processing').length,
    failed: jobs.filter((j) => j.status === 'failed').length,
  }

  return (
    <PageLayout title="Dashboard">
      {isLoading ? (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 mb-4">
          {Array.from({ length: 4 }).map((_, i) => <CardSkeleton key={i} />)}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 mb-4">
          <StatCard label="Total Jobs" value={stats.total} icon={Briefcase} />
          <StatCard label="Completed" value={stats.completed} icon={CheckCircle} />
          <StatCard label="In Progress" value={stats.pending} icon={Clock} />
          <StatCard label="Failed" value={stats.failed} icon={XCircle} />
        </div>
      )}

      <div className="rounded-md border border-border bg-card">
        <div className="px-3 py-2 border-b border-border flex items-center justify-between">
          <h2 className="text-[13px] font-semibold text-foreground">Recent Jobs</h2>
          <Link to="/jobs" className="text-[11px] text-primary hover:underline">View all</Link>
        </div>
        <table className="w-full text-[13px]">
          <thead>
            <tr className="border-b border-border">
              <th className="px-3 py-2 text-left text-[11px] font-medium uppercase tracking-wide text-muted-foreground">ID</th>
              <th className="px-3 py-2 text-left text-[11px] font-medium uppercase tracking-wide text-muted-foreground">Status</th>
              <th className="px-3 py-2 text-left text-[11px] font-medium uppercase tracking-wide text-muted-foreground">Mode</th>
              <th className="px-3 py-2 text-left text-[11px] font-medium uppercase tracking-wide text-muted-foreground">Created</th>
            </tr>
          </thead>
          <tbody>
            {jobs.slice(0, 8).map((job) => (
              <tr key={job.id} className="h-9 border-b border-border/50 hover:bg-accent transition-colors">
                <td className="px-3 py-0">
                  <Link to="/jobs/$jobId" params={{ jobId: job.id }} className="font-mono text-[12px] text-primary hover:underline">
                    {job.id.slice(0, 8)}…
                  </Link>
                </td>
                <td className="px-3 py-0"><StatusBadge status={job.status} /></td>
                <td className="px-3 py-0 text-muted-foreground">{job.mode}</td>
                <td className="px-3 py-0 text-muted-foreground text-[12px]">{new Date(job.created_at).toLocaleString()}</td>
              </tr>
            ))}
            {!isLoading && jobs.length === 0 && (
              <tr>
                <td colSpan={4} className="px-3 py-8 text-center text-muted-foreground/70 text-[13px]">No jobs yet. Submit a document to get started.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </PageLayout>
  )
}
