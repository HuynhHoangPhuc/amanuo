/** Reviews — list jobs pending human review and recent reviews. */

import { createFileRoute, Link } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { api } from '#/lib/api-client'
import { queryKeys } from '#/lib/query-keys'
import type { ReviewListResponse, JobListResponse } from '#/lib/types'
import { PageLayout } from '#/components/page-layout'
import { StatusBadge } from '#/components/status-badge'
import { PageSkeleton } from '#/components/loading-skeleton'
import { ClipboardCheck } from 'lucide-react'

export const Route = createFileRoute('/reviews')({ component: ReviewQueuePage })

function ReviewQueuePage() {
  const { data: pendingJobs, isLoading: loadingPending } = useQuery({
    queryKey: queryKeys.jobs.list('pending_review'),
    queryFn: () => api.get<JobListResponse>('/jobs?status=pending_review&limit=50'),
    refetchInterval: 5000,
  })

  const { data: reviews, isLoading: loadingReviews } = useQuery({
    queryKey: queryKeys.reviews.list(),
    queryFn: () => api.get<ReviewListResponse>('/reviews?limit=20'),
  })

  const isLoading = loadingPending || loadingReviews

  return (
    <PageLayout title="Reviews" description="Human-in-the-loop review and corrections" actions={
      <span className="text-[12px] font-medium text-muted-foreground tabular-nums">
        {pendingJobs?.total ?? 0} pending review
      </span>
    }>
      {isLoading ? (
        <PageSkeleton />
      ) : (
        <div className="space-y-5 max-w-4xl">
          {/* Pending review jobs */}
          <section>
            <h2 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
              <ClipboardCheck size={16} className="text-muted-foreground" /> Pending Review
            </h2>
            {pendingJobs?.jobs.length === 0 ? (
              <div className="rounded-lg border border-border bg-card py-8 text-center text-muted-foreground text-[13px]">
                No jobs awaiting review.
              </div>
            ) : (
              <div className="rounded-lg border border-border bg-card divide-y divide-border/50">
                {pendingJobs?.jobs.map((job) => (
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
                    <div className="flex items-center gap-4 text-[12px] text-muted-foreground">
                      {job.confidence != null && (
                        <span className={`tabular-nums ${job.confidence < 0.85 ? 'text-amber-600 dark:text-amber-400 font-medium' : ''}`}>
                          {Math.round(job.confidence * 100)}% conf
                        </span>
                      )}
                      <span className="tabular-nums">{new Date(job.created_at).toLocaleDateString()}</span>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </section>

          {/* Recent reviews */}
          <section>
            <h2 className="text-sm font-semibold text-foreground mb-3">Recent Reviews</h2>
            {reviews?.reviews.length === 0 ? (
              <div className="rounded-lg border border-border bg-card py-8 text-center text-muted-foreground text-[13px]">
                No reviews yet.
              </div>
            ) : (
              <div className="rounded-lg border border-border bg-card divide-y divide-border/50">
                {reviews?.reviews.map((review) => (
                  <div
                    key={review.id}
                    className="flex items-center justify-between px-4 py-3"
                  >
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-[12px] text-foreground">
                        {review.job_id.slice(0, 8)}
                      </span>
                      <span
                        className={`text-[12px] px-2 py-0.5 rounded-full font-medium ${
                          review.status === 'approved'
                            ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400'
                            : 'bg-primary/10 text-primary'
                        }`}
                      >
                        {review.status}
                      </span>
                      {review.corrections && (
                        <span className="text-[12px] text-muted-foreground tabular-nums">
                          {review.corrections.length} correction(s)
                        </span>
                      )}
                    </div>
                    <span className="text-[12px] text-muted-foreground tabular-nums">
                      {new Date(review.created_at).toLocaleDateString()}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      )}
    </PageLayout>
  )
}
