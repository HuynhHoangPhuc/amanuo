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
      <span className="text-sm text-gray-500">
        {pendingJobs?.total ?? 0} pending review
      </span>
    }>
      {isLoading ? (
        <PageSkeleton />
      ) : (
        <div className="space-y-6 max-w-4xl">
          {/* Pending review jobs */}
          <section>
            <h2 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
              <ClipboardCheck size={16} /> Pending Review
            </h2>
            {pendingJobs?.jobs.length === 0 ? (
              <p className="text-sm text-gray-400 py-4">No jobs awaiting review.</p>
            ) : (
              <div className="rounded-xl border border-gray-200 bg-white divide-y divide-gray-100">
                {pendingJobs?.jobs.map((job) => (
                  <Link
                    key={job.id}
                    to="/reviews/$jobId"
                    params={{ jobId: job.id }}
                    className="flex items-center justify-between px-4 py-3 hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-xs text-gray-600">{job.id.slice(0, 8)}</span>
                      <StatusBadge status={job.status} />
                    </div>
                    <div className="flex items-center gap-4 text-sm text-gray-500">
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
            <h2 className="text-sm font-semibold text-gray-700 mb-3">Recent Reviews</h2>
            {reviews?.reviews.length === 0 ? (
              <p className="text-sm text-gray-400 py-4">No reviews yet.</p>
            ) : (
              <div className="rounded-xl border border-gray-200 bg-white divide-y divide-gray-100">
                {reviews?.reviews.map((review) => (
                  <div
                    key={review.id}
                    className="flex items-center justify-between px-4 py-3"
                  >
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-xs text-gray-600">
                        {review.job_id.slice(0, 8)}
                      </span>
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                          review.status === 'approved'
                            ? 'bg-green-50 text-green-700'
                            : 'bg-blue-50 text-blue-700'
                        }`}
                      >
                        {review.status}
                      </span>
                      {review.corrections && (
                        <span className="text-xs text-gray-400">
                          {review.corrections.length} correction(s)
                        </span>
                      )}
                    </div>
                    <span className="text-sm text-gray-500">
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
