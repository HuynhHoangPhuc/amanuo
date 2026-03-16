/** Job detail page with result JSON viewer. */

import { createFileRoute, Link } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { api } from '#/lib/api-client'
import { queryKeys } from '#/lib/query-keys'
import type { JobResponse } from '#/lib/types'
import { PageLayout } from '#/components/page-layout'
import { StatusBadge } from '#/components/status-badge'
import { JsonResultViewer } from '#/components/json-result-viewer'
import { PageSkeleton } from '#/components/loading-skeleton'
import { ArrowLeft, RefreshCw } from 'lucide-react'

export const Route = createFileRoute('/jobs_/$jobId')({ component: JobDetailPage })

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start gap-4 py-2.5 border-b border-gray-50 last:border-0">
      <span className="w-36 shrink-0 text-sm text-gray-500">{label}</span>
      <span className="text-sm text-gray-900">{value}</span>
    </div>
  )
}

function JobDetailPage() {
  const { jobId } = Route.useParams()

  const { data: job, isLoading, refetch, isFetching } = useQuery({
    queryKey: queryKeys.jobs.detail(jobId),
    queryFn: () => api.get<JobResponse>(`/jobs/${jobId}`),
    refetchInterval: (q) =>
      q.state.data?.status === 'pending' || q.state.data?.status === 'processing'
        ? 2000
        : false,
  })

  return (
    <PageLayout
      title="Job Detail"
      actions={
        <div className="flex items-center gap-2">
          <Link to="/jobs" className="flex items-center gap-1.5 text-sm text-gray-600 hover:text-gray-900">
            <ArrowLeft size={14} /> Back
          </Link>
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="flex items-center gap-1.5 rounded-lg border border-gray-200 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-50"
          >
            <RefreshCw size={14} className={isFetching ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      }
    >
      {isLoading ? (
        <PageSkeleton />
      ) : job ? (
        <div className="space-y-4 max-w-3xl">
          <div className="rounded-xl border border-gray-200 bg-white p-5">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">Job Information</h2>
            <InfoRow label="Job ID" value={<span className="font-mono text-xs">{job.id}</span>} />
            <InfoRow label="Status" value={<StatusBadge status={job.status} />} />
            <InfoRow label="Mode" value={job.mode} />
            {job.cloud_provider && <InfoRow label="Provider" value={job.cloud_provider} />}
            <InfoRow label="Created" value={new Date(job.created_at).toLocaleString()} />
            {job.completed_at && (
              <InfoRow label="Completed" value={new Date(job.completed_at).toLocaleString()} />
            )}
            {job.confidence != null && (
              <InfoRow label="Confidence" value={`${Math.round(job.confidence * 100)}%`} />
            )}
            {job.error && (
              <InfoRow
                label="Error"
                value={<span className="text-red-600 text-xs">{job.error}</span>}
              />
            )}
          </div>

          {job.cost && (
            <div className="rounded-xl border border-gray-200 bg-white p-5">
              <h2 className="text-sm font-semibold text-gray-700 mb-3">Cost</h2>
              <InfoRow label="Input tokens" value={job.cost.input_tokens.toLocaleString()} />
              <InfoRow label="Output tokens" value={job.cost.output_tokens.toLocaleString()} />
              <InfoRow label="Est. cost" value={`$${job.cost.estimated_cost_usd.toFixed(6)}`} />
            </div>
          )}

          {job.result && job.result.length > 0 && (
            <JsonResultViewer results={job.result} />
          )}

          {job.status === 'pending' || job.status === 'processing' ? (
            <div className="flex items-center gap-2 text-sm text-blue-600">
              <RefreshCw size={14} className="animate-spin" />
              Auto-refreshing every 2s…
            </div>
          ) : null}
        </div>
      ) : (
        <p className="text-gray-500">Job not found.</p>
      )}
    </PageLayout>
  )
}
