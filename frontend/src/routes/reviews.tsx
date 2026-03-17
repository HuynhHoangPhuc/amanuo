/** Review queue — list jobs pending human review. */

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
  // Fetch jobs with pending_review status
  const { data: pendingJobs, isLoading: loadingPending } = useQuery({
    queryKey: queryKeys.jobs.list('pending_review'),
    queryFn: () => api.get<JobListResponse>('/jobs?status=pending_review&limit=50'),
    refetchInterval: 5000,
  })

  // Fetch recent reviews
  const { data: reviews, isLoading: loadingReviews } = useQuery({
    queryKey: queryKeys.reviews.list(),
    queryFn: () => api.get<ReviewListResponse>('/reviews?limit=20'),
  })

  const isLoading = loadingPending || loadingReviews

  return (
    <PageLayout title="Review Queue" actions={
      <span className="text-sm text-muted-foreground">
        {pendingJobs?.total ?? 0} pending review
      </span>
    }>
      {isLoading ? (
        <PageSkeleton />
      ) : (
        <div className="space-y-4 max-w-4xl">
          {/* Pending review jobs */}
          <section>
            <h2 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
              <ClipboardCheck size={16} /> Pending Review
            </h2>
            {pendingJobs?.jobs.length === 0 ? (
              <p className="text-sm text-muted-foreground/70 py-4">No jobs awaiting review.</p>
            ) : (
              <div className="rounded-md border border-border bg-card divide-y divide-border">
                {pendingJobs?.jobs.map((job) => (
                  <Link
                    key={job.id}
                    to="/reviews/$jobId"
                    params={{ jobId: job.id }}
                    className="flex items-center justify-between px-4 py-3 hover:bg-muted transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-xs text-muted-foreground">{job.id.slice(0, 8)}</span>
                      <StatusBadge status={job.status} />
                    </div>
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      {job.confidence != null && (
                        <span className={job.confidence < 0.85 ? 'text-yellow-600 font-medium' : ''}>
                          {Math.round(job.confidence * 100)}% conf
                        </span>
                      )}
                      <span>{new Date(job.created_at).toLocaleDateString()}</span>
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
              <p className="text-sm text-muted-foreground/70 py-4">No reviews yet.</p>
            ) : (
              <div className="rounded-md border border-border bg-card divide-y divide-border">
                {reviews?.reviews.map((review) => (
                  <div
                    key={review.id}
                    className="flex items-center justify-between px-4 py-3"
                  >
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-xs text-muted-foreground">
                        {review.job_id.slice(0, 8)}
                      </span>
                      <span
                        className={`text-xs px-2 py-0.5 rounded-md font-medium ${
                          review.status === 'approved'
                            ? 'bg-green-500/10 text-green-700'
                            : 'bg-primary/10 text-primary'
                        }`}
                      >
                        {review.status}
                      </span>
                      {review.corrections && (
                        <span className="text-xs text-muted-foreground/70">
                          {review.corrections.length} correction(s)
                        </span>
                      )}
                    </div>
                    <span className="text-sm text-muted-foreground">
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
