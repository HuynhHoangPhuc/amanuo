/** Review submission page for approval workflow assignments. */

import { createFileRoute } from '@tanstack/react-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '#/lib/api-client'
import { queryKeys } from '#/lib/query-keys'
import type { ReviewStatusResponse } from '#/lib/types'
import { PageLayout } from '#/components/page-layout'
import { ApprovalProgress } from '#/components/approval-progress'
import { PageSkeleton } from '#/components/loading-skeleton'
import { useState } from 'react'

export const Route = createFileRoute('/review-queue_/$jobId')({ component: ReviewJobPage })

function ReviewJobPage() {
  const { jobId } = Route.useParams()
  const queryClient = useQueryClient()
  const [reviewStatus, setReviewStatus] = useState<'approved' | 'corrected' | 'rejected' | null>(null)

  const { data: status, isLoading } = useQuery({
    queryKey: queryKeys.reviewStatus.detail(jobId),
    queryFn: () => api.get<ReviewStatusResponse>(`/jobs/${jobId}/review-status`),
  })

  const submitMutation = useMutation({
    mutationFn: (data: { status: string; corrected_result?: unknown[] }) =>
      api.post(`/jobs/${jobId}/review`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.reviewQueue.all() })
      queryClient.invalidateQueries({ queryKey: queryKeys.reviewStatus.detail(jobId) })
      queryClient.invalidateQueries({ queryKey: queryKeys.jobs.detail(jobId) })
    },
  })

  const handleSubmit = (action: 'approved' | 'corrected' | 'rejected') => {
    setReviewStatus(action)
    submitMutation.mutate({ status: action })
  }

  return (
    <PageLayout title={`Review ${jobId.slice(0, 8)}`}>
      {isLoading ? <PageSkeleton /> : (
        <div className="max-w-4xl space-y-4">
          {/* Approval progress */}
          {status && (
            <div className="rounded-lg border border-border bg-card p-4">
              <ApprovalProgress status={status} />
            </div>
          )}

          {/* Assignment list */}
          {status && (
            <div className="rounded-lg border border-border bg-card p-4">
              <h3 className="text-sm font-semibold text-foreground mb-3">Assignments</h3>
              <div className="space-y-2">
                {status.assignments.map((a) => (
                  <div key={a.id} className="flex items-center justify-between text-sm">
                    <span className="font-mono text-xs text-muted-foreground">{a.user_id.slice(0, 8)}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-md font-medium capitalize ${
                      a.status === 'approved' ? 'bg-green-500/10 text-green-700'
                        : a.status === 'corrected' ? 'bg-primary/10 text-primary'
                        : a.status === 'rejected' ? 'bg-red-500/10 text-red-700'
                        : 'bg-muted text-muted-foreground'
                    }`}>
                      {a.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Review actions */}
          {submitMutation.isSuccess ? (
            <div className="rounded-md border border-green-500/20 bg-green-500/10 p-4 text-sm text-green-700 dark:text-green-400">
              Review submitted as <strong className="capitalize">{reviewStatus}</strong>.
            </div>
          ) : (
            <div className="rounded-lg border border-border bg-card p-4">
              <h3 className="text-sm font-semibold text-foreground mb-3">Submit Review</h3>
              <div className="flex gap-3">
                <button
                  onClick={() => handleSubmit('approved')}
                  disabled={submitMutation.isPending}
                  className="px-4 py-2 text-sm bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
                >Approve</button>
                <button
                  onClick={() => handleSubmit('corrected')}
                  disabled={submitMutation.isPending}
                  className="px-4 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50"
                >Submit Corrections</button>
                <button
                  onClick={() => handleSubmit('rejected')}
                  disabled={submitMutation.isPending}
                  className="px-4 py-2 text-sm bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
                >Reject</button>
              </div>
              {submitMutation.isError && (
                <p className="text-xs text-red-600 mt-2">{(submitMutation.error as Error).message}</p>
              )}
            </div>
          )}
        </div>
      )}
    </PageLayout>
  )
}
