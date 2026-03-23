/** Dashboard: KPI overview, recent activity, and quick actions. */

import { createFileRoute, Link } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { api } from '#/lib/api-client'
import { queryKeys } from '#/lib/query-keys'
import type { JobListResponse } from '#/lib/types'
import { PageLayout } from '#/components/page-layout'
import { StatusBadge } from '#/components/status-badge'
import { CardSkeleton } from '#/components/loading-skeleton'
import {
  Briefcase,
  CheckCircle2,
  Clock,
  XCircle,
  Upload,
  FileText,
  ArrowUpRight,
} from 'lucide-react'

export const Route = createFileRoute('/')({ component: DashboardPage })

function StatCard({
  label,
  value,
  change,
  icon: Icon,
  color,
}: {
  label: string
  value: number
  change?: string
  icon: React.ElementType
  color: 'primary' | 'success' | 'warning' | 'destructive'
}) {
  const colorMap = {
    primary: 'bg-primary/10 text-primary',
    success: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
    warning: 'bg-amber-500/10 text-amber-600 dark:text-amber-400',
    destructive: 'bg-red-500/10 text-red-600 dark:text-red-400',
  }

  return (
    <div className="rounded-lg border border-border bg-card p-4 flex items-start justify-between">
      <div>
        <p className="text-[12px] font-medium text-muted-foreground uppercase tracking-wide">{label}</p>
        <p className="text-2xl font-semibold text-foreground mt-1 tabular-nums">{value}</p>
        {change && (
          <p className="text-[12px] text-muted-foreground mt-0.5">{change}</p>
        )}
      </div>
      <div className={`rounded-lg p-2.5 ${colorMap[color]}`}>
        <Icon size={18} strokeWidth={1.75} />
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
    <PageLayout title="Dashboard" description="Overview of extraction jobs and system activity">
      {/* Quick actions */}
      <div className="flex items-center gap-2 mb-5">
        <Link
          to="/jobs"
          className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-[13px] font-medium text-primary-foreground hover:bg-primary/90 transition-colors no-underline cursor-pointer"
        >
          <Upload size={14} />
          New Extraction
        </Link>
        <Link
          to="/schemas"
          className="inline-flex items-center gap-1.5 rounded-md border border-border bg-card px-3 py-1.5 text-[13px] font-medium text-foreground hover:bg-accent transition-colors no-underline cursor-pointer"
        >
          <FileText size={14} />
          Manage Schemas
        </Link>
      </div>

      {/* KPI cards */}
      {isLoading ? (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4 mb-6">
          {Array.from({ length: 4 }).map((_, i) => <CardSkeleton key={i} />)}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4 mb-6">
          <StatCard label="Total Jobs" value={stats.total} icon={Briefcase} color="primary" />
          <StatCard label="Completed" value={stats.completed} icon={CheckCircle2} color="success" />
          <StatCard label="In Progress" value={stats.pending} icon={Clock} color="warning" />
          <StatCard label="Failed" value={stats.failed} icon={XCircle} color="destructive" />
        </div>
      )}

      {/* Recent jobs table */}
      <div className="rounded-lg border border-border bg-card">
        <div className="px-4 py-3 border-b border-border flex items-center justify-between">
          <h2 className="text-sm font-semibold text-foreground">Recent Jobs</h2>
          <Link to="/jobs" className="inline-flex items-center gap-1 text-[12px] font-medium text-primary hover:text-primary/80 no-underline">
            View all
            <ArrowUpRight size={12} />
          </Link>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-[13px]">
            <thead>
              <tr className="border-b border-border">
                <th className="px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Job ID</th>
                <th className="px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Status</th>
                <th className="px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Mode</th>
                <th className="px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Created</th>
              </tr>
            </thead>
            <tbody>
              {jobs.slice(0, 8).map((job) => (
                <tr key={job.id} className="border-b border-border/50 hover:bg-accent/50 transition-colors">
                  <td className="px-4 py-2.5">
                    <Link to="/jobs/$jobId" params={{ jobId: job.id }} className="font-mono text-[12px] text-primary hover:underline">
                      {job.id.slice(0, 8)}...
                    </Link>
                  </td>
                  <td className="px-4 py-2.5"><StatusBadge status={job.status} /></td>
                  <td className="px-4 py-2.5 text-muted-foreground capitalize">{job.mode}</td>
                  <td className="px-4 py-2.5 text-muted-foreground text-[12px] tabular-nums">{new Date(job.created_at).toLocaleString()}</td>
                </tr>
              ))}
              {!isLoading && jobs.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-4 py-12 text-center text-muted-foreground text-[13px]">
                    <div className="flex flex-col items-center gap-2">
                      <Briefcase size={24} className="text-muted-foreground/40" />
                      <p>No jobs yet. Submit a document to get started.</p>
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
