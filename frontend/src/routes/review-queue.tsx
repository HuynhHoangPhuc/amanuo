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

  // Also show legacy pending_review jobs (no approval policy)
  const { data: pendingJobs, isLoading: loadingPending } = useQuery({
    queryKey: queryKeys.jobs.list('pending_review'),
    queryFn: () => api.get<JobListResponse>('/jobs?status=pending_review&limit=50'),
    refetchInterval: 5000,
  })

  const isLoading = loadingQueue || loadingPending

  return (
    <PageLayout title="Review Queue" actions={
      <span className="text-sm text-gray-500">
        {(queue?.total ?? 0) + (pendingJobs?.total ?? 0)} pending
      </span>
    }>
      {isLoading ? <PageSkeleton /> : (
        <div className="space-y-6 max-w-4xl">
          {/* Approval workflow assignments */}
          {queue && queue.queue.length > 0 && (
            <section>
              <h2 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                <ClipboardCheck size={16} /> My Assignments
              </h2>
              <div className="rounded-xl border border-gray-200 bg-white divide-y divide-gray-100">
                {queue.queue.map((item) => (
                  <Link
                    key={item.assignment_id}
                    to="/review-queue/$jobId"
                    params={{ jobId: item.job_id }}
                    className="flex items-center justify-between px-4 py-3 hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-xs text-gray-600">{item.job_id.slice(0, 8)}</span>
                      <span className="text-xs px-2 py-0.5 rounded-full bg-purple-50 text-purple-700 font-medium capitalize">
                        {item.round_type}
                      </span>
                      <span className="text-xs text-gray-400">Round {item.round_number}</span>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-gray-500">
                      {item.deadline_at && (
                        <span className="flex items-center gap-1 text-orange-600">
                          <Clock size={12} />
                          {new Date(item.deadline_at).toLocaleDateString()}
                        </span>
                      )}
                      <span>{new Date(item.created_at).toLocaleDateString()}</span>
                    </div>
                  </Link>
                ))}
              </div>
            </section>
          )}

          {/* Legacy pending review jobs */}
          {pendingJobs && pendingJobs.jobs.length > 0 && (
            <section>
              <h2 className="text-sm font-semibold text-gray-700 mb-3">Pending Review (Legacy)</h2>
              <div className="rounded-xl border border-gray-200 bg-white divide-y divide-gray-100">
                {pendingJobs.jobs.map((job) => (
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
                    <span className="text-sm text-gray-500">{new Date(job.created_at).toLocaleDateString()}</span>
                  </Link>
                ))}
              </div>
            </section>
          )}

          {!queue?.queue.length && !pendingJobs?.jobs.length && (
            <p className="text-sm text-gray-400 py-8 text-center">No reviews pending.</p>
          )}
        </div>
      )}
    </PageLayout>
  )
}
