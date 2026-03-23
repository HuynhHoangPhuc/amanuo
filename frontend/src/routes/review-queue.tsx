/** Enhanced review queue with approval workflow assignments. */

import { createFileRoute, Link } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { api } from '#/lib/api-client'
import { queryKeys } from '#/lib/query-keys'
import type { ReviewQueueItem, JobListResponse } from '#/lib/types'
import { PageLayout } from '#/components/page-layout'
import { StatusBadge } from '#/components/status-badge'
import { PageSkeleton } from '#/components/loading-skeleton'
import { ClipboardCheck, Clock } from 'lucide-react'

export const Route = createFileRoute('/review-queue')({ component: ReviewQueuePage })

function ReviewQueuePage() {
  const { data: queue, isLoading: loadingQueue } = useQuery({
    queryKey: queryKeys.reviewQueue.list(),
    queryFn: () => api.get<{ queue: ReviewQueueItem[]; total: number }>('/review-queue'),
    refetchInterval: 5000,
  })

  const { data: pendingJobs, isLoading: loadingPending } = useQuery({
    queryKey: queryKeys.jobs.list('pending_review'),
    queryFn: () => api.get<JobListResponse>('/jobs?status=pending_review&limit=50'),
    refetchInterval: 5000,
  })

  const isLoading = loadingQueue || loadingPending

  return (
    <PageLayout title="Review Queue" description="Approval workflow assignments and pending reviews" actions={
      <span className="text-[12px] font-medium text-muted-foreground tabular-nums">
        {(queue?.total ?? 0) + (pendingJobs?.total ?? 0)} pending
      </span>
    }>
      {isLoading ? <PageSkeleton /> : (
        <div className="space-y-5 max-w-4xl">
          {/* Approval workflow assignments */}
          {queue && queue.queue.length > 0 && (
            <section>
              <h2 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                <ClipboardCheck size={16} className="text-muted-foreground" /> My Assignments
              </h2>
              <div className="rounded-lg border border-border bg-card divide-y divide-border/50">
                {queue.queue.map((item) => (
                  <Link
                    key={item.assignment_id}
                    to="/review-queue/$jobId"
                    params={{ jobId: item.job_id }}
                    className="flex items-center justify-between px-4 py-3 hover:bg-accent/50 transition-colors no-underline cursor-pointer"
                  >
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-[12px] text-foreground">{item.job_id.slice(0, 8)}</span>
                      <span className="text-[12px] px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-700 dark:text-purple-400 font-medium capitalize">
                        {item.round_type}
                      </span>
                      <span className="text-[12px] text-muted-foreground tabular-nums">Round {item.round_number}</span>
                    </div>
                    <div className="flex items-center gap-3 text-[12px] text-muted-foreground">
                      {item.deadline_at && (
                        <span className="flex items-center gap-1 text-amber-600 dark:text-amber-400">
                          <Clock size={12} />
                          {new Date(item.deadline_at).toLocaleDateString()}
                        </span>
                      )}
                      <span className="tabular-nums">{new Date(item.created_at).toLocaleDateString()}</span>
                    </div>
                  </Link>
                ))}
              </div>
            </section>
          )}

          {/* Legacy pending review jobs */}
          {pendingJobs && pendingJobs.jobs.length > 0 && (
            <section>
              <h2 className="text-sm font-semibold text-foreground mb-3">Pending Review (Legacy)</h2>
              <div className="rounded-lg border border-border bg-card divide-y divide-border/50">
                {pendingJobs.jobs.map((job) => (
                  <Link
                    key={job.id}
                    to="/reviews/$jobId"
                    params={{ jobId: job.id }}
                    className="flex items-center justify-between px-4 py-3 hover:bg-accent/50 transition-colors no-underline cursor-pointer"
                  >
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-[12px] text-foreground">{job.id.slice(0, 8)}</span>
                      <StatusBadge status={job.status} />
                    </div>
                    <span className="text-[12px] text-muted-foreground tabular-nums">{new Date(job.created_at).toLocaleDateString()}</span>
                  </Link>
                ))}
              </div>
            </section>
          )}

          {!queue?.queue.length && !pendingJobs?.jobs.length && (
            <div className="rounded-lg border border-border bg-card py-12 text-center text-muted-foreground">
              <div className="flex flex-col items-center gap-2">
                <ClipboardCheck size={24} className="text-muted-foreground/40" />
                <p className="text-[13px]">No reviews pending.</p>
              </div>
            </div>
          )}
        </div>
      )}
    </PageLayout>
  )
}
