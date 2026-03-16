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
  color,
}: {
  label: string
  value: number
  icon: React.ElementType
  color: string
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 flex items-center gap-4">
      <div className={`rounded-lg p-2 ${color}`}>
        <Icon size={20} />
      </div>
      <div>
        <p className="text-2xl font-bold text-gray-900">{value}</p>
        <p className="text-sm text-gray-500">{label}</p>
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
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 mb-6">
          {Array.from({ length: 4 }).map((_, i) => <CardSkeleton key={i} />)}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 mb-6">
          <StatCard label="Total Jobs" value={stats.total} icon={Briefcase} color="bg-blue-50 text-blue-600" />
          <StatCard label="Completed" value={stats.completed} icon={CheckCircle} color="bg-green-50 text-green-600" />
          <StatCard label="In Progress" value={stats.pending} icon={Clock} color="bg-yellow-50 text-yellow-600" />
          <StatCard label="Failed" value={stats.failed} icon={XCircle} color="bg-red-50 text-red-600" />
        </div>
      )}

      <div className="rounded-xl border border-gray-200 bg-white">
        <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-700">Recent Jobs</h2>
          <Link to="/jobs" className="text-xs text-blue-600 hover:underline">View all</Link>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 text-xs text-gray-500">
              <th className="px-5 py-2 text-left font-medium">ID</th>
              <th className="px-5 py-2 text-left font-medium">Status</th>
              <th className="px-5 py-2 text-left font-medium">Mode</th>
              <th className="px-5 py-2 text-left font-medium">Created</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {jobs.slice(0, 8).map((job) => (
              <tr key={job.id} className="hover:bg-gray-50">
                <td className="px-5 py-2.5">
                  <Link to="/jobs/$jobId" params={{ jobId: job.id }} className="font-mono text-xs text-blue-600 hover:underline">
                    {job.id.slice(0, 8)}…
                  </Link>
                </td>
                <td className="px-5 py-2.5"><StatusBadge status={job.status} /></td>
                <td className="px-5 py-2.5 text-gray-600">{job.mode}</td>
                <td className="px-5 py-2.5 text-gray-500 text-xs">{new Date(job.created_at).toLocaleString()}</td>
              </tr>
            ))}
            {!isLoading && jobs.length === 0 && (
              <tr>
                <td colSpan={4} className="px-5 py-8 text-center text-gray-400 text-sm">No jobs yet. Submit a document to get started.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </PageLayout>
  )
}
