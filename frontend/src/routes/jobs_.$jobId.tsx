/** Job detail page with result JSON viewer. */

import { createFileRoute, Link } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { api } from '#/lib/api-client'
import { queryKeys } from '#/lib/query-keys'
import type { JobResponse, ReviewStatusResponse } from '#/lib/types'
import { PageLayout } from '#/components/page-layout'
import { StatusBadge } from '#/components/status-badge'
import { JsonResultViewer } from '#/components/json-result-viewer'
import { ApprovalProgress } from '#/components/approval-progress'
import { PageSkeleton } from '#/components/loading-skeleton'
import { ArrowLeft, RefreshCw, ClipboardCheck } from 'lucide-react'

export const Route = createFileRoute('/jobs_/$jobId')({ component: JobDetailPage })

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start gap-4 py-2.5 border-b border-border/30 last:border-0">
      <span className="w-36 shrink-0 text-sm text-muted-foreground">{label}</span>
      <span className="text-sm text-foreground">{value}</span>
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

  const { data: reviewStatus } = useQuery({
    queryKey: queryKeys.reviewStatus.detail(jobId),
    queryFn: () => api.get<ReviewStatusResponse>(`/jobs/${jobId}/review-status`),
    enabled: job?.status === 'pending_review',
    retry: false,
  })

  return (
    <PageLayout
      title="Job Detail"
      actions={
        <div className="flex items-center gap-2">
          <Link to="/jobs" className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
            <ArrowLeft size={14} /> Back
          </Link>
          {job?.status === 'pending_review' && (
            <Link
              to="/reviews/$jobId"
              params={{ jobId }}
              className="flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90"
            >
              <ClipboardCheck size={14} /> Review
            </Link>
          )}
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-sm text-muted-foreground hover:bg-muted disabled:opacity-50"
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
          <div className="rounded-xl border border-border bg-card p-5">
            <h2 className="text-sm font-semibold text-foreground mb-3">Job Information</h2>
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

          {reviewStatus && (
            <div className="rounded-xl border border-border bg-card p-5">
              <h2 className="text-sm font-semibold text-foreground mb-3">Approval Progress</h2>
              <ApprovalProgress status={reviewStatus} />
            </div>
          )}

          {job.cost && (
            <div className="rounded-xl border border-border bg-card p-5">
              <h2 className="text-sm font-semibold text-foreground mb-3">Cost</h2>
              <InfoRow label="Input tokens" value={job.cost.input_tokens.toLocaleString()} />
              <InfoRow label="Output tokens" value={job.cost.output_tokens.toLocaleString()} />
              <InfoRow label="Est. cost" value={`$${job.cost.estimated_cost_usd.toFixed(6)}`} />
            </div>
          )}

          {job.result && job.result.length > 0 && (
            <JsonResultViewer results={job.result} />
          )}

          {job.status === 'pending' || job.status === 'processing' ? (
            <div className="flex items-center gap-2 text-sm text-primary">
              <RefreshCw size={14} className="animate-spin" />
              Auto-refreshing every 2s…
            </div>
          ) : null}
        </div>
      ) : (
        <p className="text-muted-foreground">Job not found.</p>
      )}
    </PageLayout>
  )
}
